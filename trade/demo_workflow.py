#!/usr/bin/env python3
"""
Demo workflow: create input Excel, run verification on 20 companies,
use Companies House, ITA CSL, ICIJ Offshore Leaks, and UN Comtrade,
and generate a PDF report with tables.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
from dotenv import load_dotenv

from config import Config
from modules.registry_checker import RegistryChecker
from modules.sanctions_checker import SanctionsChecker
from modules.offshore_checker import OffshoreChecker
from modules.trade_checker import TradeChecker
from modules.risk_scorer import RiskScorer


INPUT_XLSX = Path('demo_input.xlsx')
OUTPUT_ROOT = Path('demo_output')

COMPANY_METADATA = [
    {"company_name": "Apple Inc.", "country": "US", "hs_code": "85", "sector": "Electronics"},
    {"company_name": "Microsoft Corporation", "country": "US", "hs_code": "85", "sector": "Electronics"},
    {"company_name": "Tesla, Inc.", "country": "US", "hs_code": "87", "sector": "Vehicles"},
    {"company_name": "Boeing Company", "country": "US", "hs_code": "88", "sector": "Aircraft"},
    {"company_name": "Exxon Mobil Corporation", "country": "US", "hs_code": "27", "sector": "Petroleum"},
    {"company_name": "Pfizer Inc.", "country": "US", "hs_code": "30", "sector": "Pharmaceuticals"},
    {"company_name": "Unilever PLC", "country": "GB", "hs_code": "34", "sector": "Consumer goods"},
    {"company_name": "HSBC Holdings plc", "country": "GB", "hs_code": "71", "sector": "Financial services"},
    {"company_name": "AstraZeneca plc", "country": "GB", "hs_code": "30", "sector": "Pharmaceuticals"},
    {"company_name": "BP p.l.c.", "country": "GB", "hs_code": "27", "sector": "Petroleum"},
    {"company_name": "Rolls-Royce Holdings plc", "country": "GB", "hs_code": "84", "sector": "Industrial machinery"},
    {"company_name": "BAE Systems plc", "country": "GB", "hs_code": "93", "sector": "Defense"},
    {"company_name": "Appleby Limited", "country": "WS", "hs_code": "84", "sector": "Corporate services"},
    {"company_name": "Mossack Fonseca & Co. (Samoa) Limited", "country": "WS", "hs_code": "84", "sector": "Corporate services"},
    {"company_name": "Gazprom", "country": "RU", "hs_code": "27", "sector": "Energy"},
    {"company_name": "Rosneft", "country": "RU", "hs_code": "27", "sector": "Energy"},
    {"company_name": "PDVSA", "country": "VE", "hs_code": "27", "sector": "Energy"},
    {"company_name": "Bank Melli Iran", "country": "IR", "hs_code": "71", "sector": "Financial services"},
    {"company_name": "Mahan Air", "country": "IR", "hs_code": "88", "sector": "Aviation"},
    {"company_name": "Korea Mining Development Trading Corporation (KOMID)", "country": "KP", "hs_code": "93", "sector": "Defense"},
]

TODO_BUGS = [
    "ITA CSL fuzzy search returns false positives for common names; add exact/score thresholds.",
    "SEC ticker list is downloaded per US company; cache once per run to reduce latency.",
    "UN Comtrade country mapping is partial; replace with full ISO2->M49 mapping.",
    "ICIJ CSVs are loaded fully into memory; add indexing or database-backed search.",
]


def ensure_icij_data() -> None:
    required_files = [
        'nodes-entities.csv',
        'nodes-officers.csv',
        'relationships.csv',
    ]
    data_path = Path(Config.ICIJ_DATA_PATH)
    data_path.mkdir(parents=True, exist_ok=True)

    if all((data_path / f).exists() for f in required_files):
        return

    url = 'https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip'
    zip_path = data_path / 'full-oldb.LATEST.zip'

    import requests
    import zipfile

    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(zip_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(data_path)


def create_input_excel() -> None:
    names = [c["company_name"] for c in COMPANY_METADATA]
    df = pd.DataFrame({"company_name": names})
    df.to_excel(INPUT_XLSX, index=False)


def load_company_metadata() -> Dict[str, Dict[str, Any]]:
    meta = {}
    for item in COMPANY_METADATA:
        meta[item["company_name"]] = item
    return meta


def run_checks(companies: List[str], output_dir: Path) -> List[Dict[str, Any]]:
    registry_checker = RegistryChecker()
    sanctions_checker = SanctionsChecker()
    offshore_checker = OffshoreChecker()
    trade_checker = TradeChecker()
    risk_scorer = RiskScorer()

    metadata = load_company_metadata()
    results = []

    for name in companies:
        meta = metadata.get(name, {})
        country = meta.get("country", "US")
        hs_code = meta.get("hs_code")

        registry_result = registry_checker.check(name, country)
        sanctions_result = sanctions_checker.check(name, [])
        offshore_result = offshore_checker.check(name, [])
        trade_result = trade_checker.check(name, country_code=country, industry_hs_code=hs_code)

        risk = risk_scorer.calculate_score(
            registry_result,
            sanctions_result,
            offshore_result,
            trade_result
        )

        record = {
            "company_name": name,
            "country": country,
            "hs_code": hs_code,
            "sector": meta.get("sector"),
            "registry": registry_result,
            "sanctions": sanctions_result,
            "offshore": offshore_result,
            "trade": trade_result,
            "risk_assessment": risk,
        }

        results.append(record)

        safe_name = name.replace('/', '_').replace('\\', '_').replace('"', '')
        out_path = output_dir / f"{safe_name}.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=2, ensure_ascii=False, default=str)

        time.sleep(0.2)

    registry_checker.close()
    sanctions_checker.close()
    trade_checker.close()

    return results


def build_summary_tables(results: List[Dict[str, Any]]):
    summary_rows = []
    sanctions_rows = []
    offshore_rows = []
    trade_rows = []

    for r in results:
        reg = r.get('registry', {})
        sanc = r.get('sanctions', {})
        off = r.get('offshore', {})
        trade = r.get('trade', {})
        risk = r.get('risk_assessment', {})

        summary_rows.append({
            'Company': r['company_name'],
            'Country': r['country'],
            'HS': r.get('hs_code') or '',
            'Registry Found': reg.get('found', False),
            'Sanctions Hits': sanc.get('sanctions_hits', 0),
            'Offshore Hits': off.get('offshore_hits', 0),
            'Trade Value (USD)': round(trade.get('country_trade_volume', 0.0), 2),
            'Risk Level': risk.get('risk_level'),
            'Risk Score': risk.get('risk_score'),
        })

        for match in sanc.get('matches', [])[:3]:
            sanctions_rows.append({
                'Company': r['company_name'],
                'Match Name': match.get('name', ''),
                'Source': match.get('source', ''),
                'Programs': ", ".join(match.get('programs', [])[:3]) if isinstance(match.get('programs'), list) else ''
            })

        for match in off.get('matches', [])[:3]:
            offshore_rows.append({
                'Company': r['company_name'],
                'Match Name': match.get('name', ''),
                'Jurisdiction': match.get('jurisdiction', ''),
                'Source': match.get('source_investigation', ''),
            })

        trade_rows.append({
            'Company': r['company_name'],
            'Country': r['country'],
            'HS': r.get('hs_code') or '',
            'Records': trade.get('records_count', 0),
            'Trade Value (USD)': round(trade.get('country_trade_volume', 0.0), 2),
        })

    return summary_rows, sanctions_rows, offshore_rows, trade_rows


def write_excel_report(
    output_path: Path,
    input_companies: List[str],
    summary_rows,
    sanctions_rows,
    offshore_rows,
    trade_rows,
    workflow_notes: List[str]
):
    overview = pd.DataFrame({
        'item': [
            'Generated (UTC)',
            'Input file',
            'ICIJ data path',
            'Companies count',
        ],
        'value': [
            datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
            str(INPUT_XLSX),
            str(Config.ICIJ_DATA_PATH),
            len(input_companies),
        ]
    })
    workflow = pd.DataFrame({'workflow_step': workflow_notes})
    todo = pd.DataFrame({'todo_or_bug': TODO_BUGS})
    inputs = pd.DataFrame({'company_name': input_companies})

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        overview.to_excel(writer, sheet_name='overview', index=False)
        inputs.to_excel(writer, sheet_name='inputs', index=False)
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name='summary', index=False)
        pd.DataFrame(sanctions_rows).to_excel(writer, sheet_name='sanctions_sample', index=False)
        pd.DataFrame(offshore_rows).to_excel(writer, sheet_name='offshore_sample', index=False)
        pd.DataFrame(trade_rows).to_excel(writer, sheet_name='trade_summary', index=False)
        workflow.to_excel(writer, sheet_name='workflow', index=False)
        todo.to_excel(writer, sheet_name='todo_bugs', index=False)


def write_workflow_log(output_dir: Path, report_path: Path, input_path: Path, results_dir: Path):
    lines = [
        "Demo workflow completed:",
        f"- Input Excel: {input_path}",
        f"- Results JSON folder: {results_dir}",
        f"- Excel report: {report_path}",
        f"- ICIJ data path: {Config.ICIJ_DATA_PATH}",
    ]
    log_path = output_dir / 'workflow_steps.md'
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


if __name__ == '__main__':
    load_dotenv(dotenv_path='.env')

    ensure_icij_data()
    create_input_excel()

    run_id = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    output_dir = OUTPUT_ROOT / f"demo_{run_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir = output_dir / 'results'
    results_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(INPUT_XLSX)
    companies = df.iloc[:, 0].dropna().tolist()

    results = run_checks(companies, results_dir)

    summary_rows, sanctions_rows, offshore_rows, trade_rows = build_summary_tables(results)

    report_path = output_dir / 'company_verification_report.xlsx'
    workflow_notes = [
        "Input list created as demo_input.xlsx (first column only).",
        "Companies House API used for GB companies; SEC EDGAR for US companies.",
        "ITA Consolidated Screening List used for sanctions screening.",
        "ICIJ Offshore Leaks CSVs loaded from data/icij_offshore.",
        "UN Comtrade v1 API used for country-level trade alignment by HS code.",
    ]
    write_excel_report(
        report_path,
        companies,
        summary_rows,
        sanctions_rows,
        offshore_rows,
        trade_rows,
        workflow_notes
    )

    write_workflow_log(output_dir, report_path, INPUT_XLSX, results_dir)

    print(f"Done. Report: {report_path}")
