#!/usr/bin/env python3
"""Setup Wizard for Company Research Tool.

Interactive setup script for first-time installation.
Downloads databases, configures API keys, and verifies installation.

Run with: python setup_wizard.py
"""

import os
import sys
import subprocess
from pathlib import Path


# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.END}\n")


def print_step(num: int, text: str):
    """Print a step."""
    print(f"{Colors.CYAN}[Step {num}]{Colors.END} {text}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}[OK] {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}[!] {text}{Colors.END}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}[X] {text}{Colors.END}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}[i] {text}{Colors.END}")


def ask_yes_no(question: str, default: bool = True) -> bool:
    """Ask a yes/no question."""
    default_str = "[Y/n]" if default else "[y/N]"
    response = input(f"{question} {default_str}: ").strip().lower()

    if not response:
        return default

    return response in ('y', 'yes')


def check_python_version():
    """Check Python version is 3.9+."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print_error(f"Python 3.9+ required. You have {version.major}.{version.minor}")
        return False

    print_success(f"Python version: {version.major}.{version.minor}.{version.micro}")
    return True


def check_uv_available():
    """Check if uv is installed."""
    try:
        result = subprocess.run(
            ['uv', '--version'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_dependencies():
    """Check and install dependencies using uv."""
    print_step(1, "Checking dependencies...")

    pyproject_file = Path(__file__).parent / 'pyproject.toml'

    if not pyproject_file.exists():
        print_error("pyproject.toml not found!")
        return False

    # Check if uv is available
    if not check_uv_available():
        print_error("uv is not installed!")
        print_info("Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
        print_info("Or visit: https://docs.astral.sh/uv/getting-started/installation/")
        return False

    print_success("uv is available")

    # Check if .venv exists and has packages
    venv_dir = Path(__file__).parent / '.venv'

    # Try importing key packages to see if we need to sync
    missing = []
    packages = ['streamlit', 'pandas', 'requests', 'plotly', 'fitz']

    for pkg in packages:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing or not venv_dir.exists():
        if missing:
            print_warning(f"Missing packages: {', '.join(missing)}")
        else:
            print_info("Virtual environment not found")

        if ask_yes_no("Run 'uv sync' to install dependencies?"):
            try:
                subprocess.check_call(['uv', 'sync'], cwd=Path(__file__).parent)
                print_success("Dependencies installed successfully!")
            except subprocess.CalledProcessError:
                print_error("Failed to install dependencies")
                return False
    else:
        print_success("All dependencies installed")

    return True


def setup_directories():
    """Create required directories."""
    print_step(2, "Setting up directories...")

    dirs = [
        'data',
        'data/pdfs',
        'data/opensanctions',
        'data/icij',
        'data/examples',
        'docs',
    ]

    for dir_path in dirs:
        full_path = Path(__file__).parent / dir_path
        full_path.mkdir(parents=True, exist_ok=True)

    print_success("Directories created")
    return True


def setup_env_file():
    """Configure environment variables."""
    print_step(3, "Configuring API keys...")

    env_file = Path(__file__).parent / '.env'
    env_example = Path(__file__).parent / '.env.example'

    # Check if .env already exists
    if env_file.exists():
        print_info(".env file already exists")

        # Read current values
        current = {}
        with open(env_file, encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    current[key] = value

        if current.get('BRAVE_API_KEY'):
            print_success(f"Brave API key configured: {current['BRAVE_API_KEY'][:8]}...")

        if ask_yes_no("Reconfigure API keys?", default=False):
            pass  # Continue to configuration
        else:
            return True

    print_info("""
API keys enable real-time data enrichment:
- Brave Search API: Search the web for company information
- OpenCorporates API: Access global corporate registry data

Both APIs have free tiers. You can skip this and use mock data for demo.
""")

    brave_key = input("Enter Brave Search API key (or press Enter to skip): ").strip()
    oc_key = input("Enter OpenCorporates API token (or press Enter to skip): ").strip()

    # Write .env file
    with open(env_file, 'w', encoding='utf-8') as f:
        if brave_key:
            f.write(f"BRAVE_API_KEY={brave_key}\n")
        if oc_key:
            f.write(f"OPENCORPORATES_API_TOKEN={oc_key}\n")
        f.write("RATE_LIMIT_DELAY=2\n")

    if brave_key or oc_key:
        print_success("API keys configured")
    else:
        print_warning("No API keys configured - will use mock data")

    return True


def download_datasets():
    """Download external datasets."""
    print_step(4, "Downloading datasets...")

    print_info("""
Available datasets:

1. OpenSanctions OFAC (Required for sanctions screening)
   - US Treasury OFAC press releases
   - ~10,000 sanctioned entities
   - Size: ~10 MB

2. OpenSanctions Consolidated (Recommended)
   - Global sanctions from multiple sources
   - ~100,000 entities
   - Size: ~50 MB

3. ICIJ Offshore Leaks (Optional - Large)
   - Panama Papers, Paradise Papers, etc.
   - 810,000+ offshore entities
   - Size: ~500 MB download, ~1 GB extracted

4. OpenSanctions PEPs (Optional)
   - Politically Exposed Persons
   - ~1 million entities
   - Size: ~100 MB
""")

    # OFAC (always recommended)
    if ask_yes_no("Download OpenSanctions OFAC data? (Recommended)"):
        download_opensanctions_ofac()

    # Consolidated sanctions
    if ask_yes_no("Download OpenSanctions Consolidated sanctions?"):
        download_opensanctions_consolidated()

    # ICIJ Offshore
    if ask_yes_no("Download ICIJ Offshore Leaks? (Large - 500MB+)", default=False):
        download_icij_offshore()

    # PEPs
    if ask_yes_no("Download OpenSanctions PEPs data?", default=False):
        download_opensanctions_peps()

    return True


def download_opensanctions_ofac():
    """Download OFAC press releases dataset."""
    cache_dir = Path(__file__).parent / 'data' / 'opensanctions'
    names_path = cache_dir / 'us_ofac_press_releases.names.txt'

    # Check if already exists
    if names_path.exists():
        with open(names_path, encoding='utf-8') as f:
            count = sum(1 for _ in f)
        print_success(f"Already exists: {names_path}")
        print_info(f"Total OFAC names: {count:,}")
        if not ask_yes_no("Re-download anyway?", default=False):
            return
        print_info("Re-downloading...")

    print_info("Downloading OpenSanctions OFAC data...")

    try:
        from scrapers.opensanctions import OpenSanctionsClient

        client = OpenSanctionsClient()

        # Download FTM entities
        filepath = client.download_dataset('ofac_press_releases', force=True)
        if filepath:
            print_success(f"Downloaded: {filepath}")

        # Download names list
        names_path = client.download_names_list('ofac_press_releases')
        if names_path:
            print_success(f"Names list: {names_path}")

            # Count entries
            with open(names_path, encoding='utf-8') as f:
                count = sum(1 for _ in f)
            print_info(f"Total OFAC names: {count:,}")

    except Exception as e:
        print_error(f"Failed to download OFAC data: {e}")


def download_opensanctions_consolidated():
    """Download consolidated sanctions dataset."""
    output_dir = Path(__file__).parent / 'data' / 'opensanctions'
    output_path = output_dir / 'consolidated_names.txt'

    # Check if already exists
    if output_path.exists():
        with open(output_path, encoding='utf-8') as f:
            count = sum(1 for _ in f)
        print_success(f"Already exists: {output_path}")
        print_info(f"Total consolidated sanctions names: {count:,}")
        if not ask_yes_no("Re-download anyway?", default=False):
            return
        print_info("Re-downloading...")

    print_info("Downloading OpenSanctions Consolidated sanctions...")

    try:
        import requests

        url = "https://data.opensanctions.org/datasets/latest/sanctions/names.txt"
        output_dir.mkdir(parents=True, exist_ok=True)

        response = requests.get(url, timeout=120)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            f.write(response.content)

        with open(output_path, encoding='utf-8') as f:
            count = sum(1 for _ in f)

        print_success(f"Downloaded: {output_path}")
        print_info(f"Total consolidated sanctions names: {count:,}")

    except Exception as e:
        print_error(f"Failed to download consolidated sanctions: {e}")


def download_opensanctions_peps():
    """Download PEPs dataset."""
    output_dir = Path(__file__).parent / 'data' / 'opensanctions'
    output_path = output_dir / 'peps_names.txt'

    # Check if already exists
    if output_path.exists():
        with open(output_path, encoding='utf-8') as f:
            count = sum(1 for _ in f)
        print_success(f"Already exists: {output_path}")
        print_info(f"Total PEP names: {count:,}")
        if not ask_yes_no("Re-download anyway?", default=False):
            return
        print_info("Re-downloading...")

    print_info("Downloading OpenSanctions PEPs data...")

    try:
        import requests

        url = "https://data.opensanctions.org/datasets/latest/peps/names.txt"
        output_dir.mkdir(parents=True, exist_ok=True)

        response = requests.get(url, timeout=300)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            f.write(response.content)

        with open(output_path, encoding='utf-8') as f:
            count = sum(1 for _ in f)

        print_success(f"Downloaded: {output_path}")
        print_info(f"Total PEP names: {count:,}")

    except Exception as e:
        print_error(f"Failed to download PEPs data: {e}")


def download_icij_offshore():
    """Download ICIJ Offshore Leaks database."""
    icij_dir = Path(__file__).parent / 'data' / 'icij' / 'csv'

    # Check if already exists
    if icij_dir.exists():
        csv_files = list(icij_dir.glob('*.csv'))
        if csv_files:
            print_success(f"Already exists: {icij_dir}")
            print_info(f"Found {len(csv_files)} CSV files")
            if not ask_yes_no("Re-download anyway?", default=False):
                # Still offer to build names index
                names_file = Path(__file__).parent / 'data' / 'icij' / 'offshore_names.txt'
                if not names_file.exists():
                    if ask_yes_no("Build names index file for fast lookups?"):
                        try:
                            from scrapers.icij_offshore import ICIJOffshoreClient
                            client = ICIJOffshoreClient()
                            names_file = client.build_names_file()
                            print_success(f"Names index: {names_file}")
                        except Exception as e:
                            print_error(f"Failed to build names index: {e}")
                return
            print_info("Re-downloading...")

    print_info("Downloading ICIJ Offshore Leaks database...")
    print_warning("This is a large download (~500 MB) and may take several minutes.")

    try:
        from scrapers.icij_offshore import ICIJOffshoreClient

        client = ICIJOffshoreClient()
        result = client.download_database(force=True)

        if result:
            print_success(f"Downloaded and extracted to: {result}")

            # Build names file
            if ask_yes_no("Build names index file for fast lookups?"):
                names_file = client.build_names_file()
                print_success(f"Names index: {names_file}")

    except Exception as e:
        print_error(f"Failed to download ICIJ data: {e}")


def build_fraud_database():
    """Build the combined fraud database."""
    print_step(5, "Building fraud database...")

    if ask_yes_no("Build combined fraud database from all sources?"):
        try:
            result = subprocess.run(
                ['uv', 'run', 'python', 'combine_all_sources.py'],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=Path(__file__).parent
            )

            if result.returncode == 0:
                print_success("Fraud database built successfully!")

                # Show summary
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines[-10:]:
                    print(f"  {line}")
            else:
                print_error(f"Build failed: {result.stderr}")

        except Exception as e:
            print_error(f"Failed to build database: {e}")
    else:
        print_info("Skipped database build. Run manually: uv run python combine_all_sources.py")

    return True


def verify_installation():
    """Verify the installation is working."""
    print_step(6, "Verifying installation...")

    checks = []

    # Check data directory
    data_dir = Path(__file__).parent / 'data'
    if data_dir.exists():
        checks.append(("Data directory", True))
    else:
        checks.append(("Data directory", False))

    # Check for fraud database
    fraud_db = data_dir / 'fraudulent_companies.csv'
    if fraud_db.exists():
        import pandas as pd
        df = pd.read_csv(fraud_db)
        checks.append((f"Fraud database ({len(df):,} records)", True))
    else:
        checks.append(("Fraud database", False))

    # Check for OFAC names
    ofac_names = data_dir / 'opensanctions' / 'us_ofac_press_releases.names.txt'
    if ofac_names.exists():
        with open(ofac_names, encoding='utf-8') as f:
            count = sum(1 for _ in f)
        checks.append((f"OFAC names ({count:,} entries)", True))
    else:
        checks.append(("OFAC names", False))

    # Check for ICIJ data
    icij_dir = data_dir / 'icij' / 'csv'
    if icij_dir.exists():
        checks.append(("ICIJ Offshore Leaks", True))
    else:
        checks.append(("ICIJ Offshore Leaks (optional)", None))

    # Print results
    print("\nInstallation Status:")
    for name, status in checks:
        if status is True:
            print_success(name)
        elif status is False:
            print_error(name)
        else:
            print_warning(name)

    return True


def print_next_steps():
    """Print next steps for the user."""
    print_header("Setup Complete!")

    print(f"""
{Colors.GREEN}Your Company Research Tool is ready to use!{Colors.END}

{Colors.BOLD}To start the application:{Colors.END}
    uv run streamlit run app.py

{Colors.BOLD}The app will open in your browser at:{Colors.END}
    http://localhost:8501

{Colors.BOLD}Quick Start Guide:{Colors.END}
1. Upload an Excel/CSV file with company names
2. Click "Analyze Companies" to run risk assessment
3. View risk scores and export results

{Colors.BOLD}Key Features:{Colors.END}
- Upload & Analyze: Batch company risk assessment
- Sanctions Screening: Check against OFAC and other lists
- Fraud Database: Browse {Colors.CYAN}7,000+{Colors.END} fraud cases
- Data Management: Update and refresh datasets

{Colors.BOLD}Documentation:{Colors.END}
- README.md: Full documentation
- docs/BRAVE_API_RESPONSE.md: API response reference

{Colors.BOLD}Get API Keys (for real-time data):{Colors.END}
- Brave Search: https://api-dashboard.search.brave.com
- OpenCorporates: https://opencorporates.com

{Colors.YELLOW}Note: Without API keys, the tool uses mock data for demo purposes.{Colors.END}
""")


def main():
    """Run the setup wizard."""
    print_header("Company Research Tool - Setup Wizard")

    print(f"""
Welcome! This wizard will help you set up the Company Research Tool.

{Colors.BOLD}What this wizard does:{Colors.END}
1. Check Python version and dependencies
2. Create required directories
3. Configure API keys (optional)
4. Download datasets for sanctions screening
5. Build the fraud database
6. Verify installation
""")

    if not ask_yes_no("Continue with setup?"):
        print("Setup cancelled.")
        return

    # Run setup steps
    if not check_python_version():
        return

    if not check_dependencies():
        return

    setup_directories()
    setup_env_file()
    download_datasets()
    build_fraud_database()
    verify_installation()
    print_next_steps()


if __name__ == '__main__':
    main()
