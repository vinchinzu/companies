
● Great question. Let me think through open data sources that could strengthen entity resolution and corroborate legitimacy signals.

  Trade & Customs Data

  Import/Export Records:
  - USA Trade Online (census.gov) - US import/export statistics by company
  - ImportGenius / Panjiva (partial free) - Bill of lading data showing actual shipments
  - UN Comtrade - International trade flows by country/commodity
  - EU TARIC - European customs tariff data

  Why useful: Real trading companies have actual shipment records. Shell companies typically have zero or suspicious trade patterns (e.g., only "consulting services" imports).

  Beneficial Ownership & Corporate Registries

  Open Registries:
  - OpenCorporates (already using) - 200M+ companies globally
  - UK Companies House API - Free, excellent data quality, includes officers/filings
  - OpenOwnership Register - Beneficial ownership data from multiple jurisdictions
  - GLEIF (gleif.org) - Legal Entity Identifiers (LEI) database
  - EU Business Registers - BRIS interconnection system
  - OpenSanctions - Consolidated sanctions/PEP data

  Why useful: Cross-reference officer names, addresses, registration dates across jurisdictions. Shell companies often share officers/addresses with other suspicious entities.

  Financial & Regulatory Data

  SEC/Financial:
  - SEC EDGAR - All public company filings (10-K, 8-K, etc.)
  - FINRA BrokerCheck - Broker/advisor disciplinary history
  - FDIC BankFind - Bank institution data
  - SEC IAPD - Investment adviser registration

  Sanctions/Watchlists:
  - OFAC SDN List - US Treasury sanctions
  - EU Sanctions Map - European sanctions
  - UN Security Council Sanctions
  - World Bank Debarment List - Entities banned from WB projects

  Why useful: Legitimate financial entities have regulatory footprints. Cross-reference against sanctions for immediate red flags.

  Court & Legal Records

  Sources:
  - PACER/RECAP (courtlistener.com) - US federal court records
  - SEC Litigation Releases (already scraping)
  - DOJ Press Releases - Criminal prosecutions
  - State Attorney General - State-level enforcement
  - ICIJ Offshore Leaks Database - Panama/Paradise Papers entities

  Why useful: Prior litigation, especially SEC/DOJ actions, is strong fraud signal. ICIJ data directly identifies offshore shell structures.

  Address & Geolocation

  Sources:
  - Google Places API - Verify business addresses exist
  - OpenStreetMap/Nominatim - Geocoding and address validation
  - Registered Agent Databases - Identify mass-registration addresses
  - Virtual Office Provider Lists - Known virtual office addresses

  Why useful: Shell companies often use:
  - Virtual office addresses (Regus, WeWork)
  - Registered agent addresses shared by thousands of companies
  - Non-existent or residential addresses for "corporate HQ"

  Domain & Web Presence

  Sources:
  - WHOIS databases (whois.domaintools.com)
  - Wayback Machine API - Historical website snapshots
  - Certificate Transparency Logs - SSL certificate history
  - BuiltWith - Technology stack detection
  - SimilarWeb (limited free) - Traffic estimates

  Why useful:
  - Domain age vs. claimed company age discrepancy
  - Website created right before fraud
  - No historical web presence for "established" company
  - Shared hosting with other suspicious domains

  News & Adverse Media

  Sources:
  - GDELT Project - Global news monitoring
  - MediaCloud - News archive and analysis
  - Event Registry - News event extraction
  - Google News API - Recent coverage

  Why useful: Adverse media screening is standard KYC. Legitimate companies have press coverage; shell companies have none or only negative coverage.

  Practical Entity Resolution Strategy

  ┌─────────────────────────────────────────────────────────────────┐
  │                    ENTITY RESOLUTION FLOW                        │
  ├─────────────────────────────────────────────────────────────────┤
  │                                                                  │
  │  Input: Company Name + Jurisdiction                              │
  │           │                                                      │
  │           ▼                                                      │
  │  ┌─────────────────┐                                            │
  │  │ Fuzzy Name Match │ ──► OpenCorporates, GLEIF, Companies House│
  │  └────────┬────────┘                                            │
  │           │                                                      │
  │           ▼                                                      │
  │  ┌─────────────────┐                                            │
  │  │ Address Cluster │ ──► Find other entities at same address    │
  │  └────────┬────────┘                                            │
  │           │                                                      │
  │           ▼                                                      │
  │  ┌─────────────────┐                                            │
  │  │ Officer Network │ ──► Graph of shared directors/officers     │
  │  └────────┬────────┘                                            │
  │           │                                                      │
  │           ▼                                                      │
  │  ┌─────────────────┐                                            │
  │  │ Sanctions Check │ ──► OFAC, UN, EU, OpenSanctions            │
  │  └────────┬────────┘                                            │
  │           │                                                      │
  │           ▼                                                      │
  │  ┌─────────────────┐                                            │
  │  │ Trade Activity  │ ──► Import/export records existence        │
  │  └────────┬────────┘                                            │
  │           │                                                      │
  │           ▼                                                      │
  │  Consolidated Entity Profile + Risk Score                        │
  │                                                                  │
  └─────────────────────────────────────────────────────────────────┘

  High-Value Additions for This Tool

  Immediate/Easy:
  1. OpenSanctions API - Free, consolidates 80+ sanction lists
  2. UK Companies House - Free API, rich officer data
  3. ICIJ Offshore Leaks - Downloadable, direct shell company matches
  4. GLEIF API - Free, LEI validation

  Medium Effort:
  5. Address clustering - Flag when 100+ companies share one address
  6. Officer network graph - Visualize shared directors
  7. Domain age check - Compare to claimed incorporation date

  Higher Effort:
  8. Trade data integration - Import Genius or similar
  9. Court records search - PACER/CourtListener integration
  10. News sentiment - GDELT adverse media screening

  Would you like me to implement any of these integrations? The OpenSanctions and UK Companies House APIs would add significant value with relatively low effort.
