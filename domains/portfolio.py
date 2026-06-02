import re
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pypdf

from core.memory.manager import MemoryManager

logger = logging.getLogger("mithrandir")

ACCOUNT_MAP = {
    "7SL3547517": "personal_brokerage",
    "7SZ1953714": "roth_ira",
    "6SB2431113": "smart_portfolio",
}

ACCOUNT_LABELS = {
    "personal_brokerage": "Personal Brokerage",
    "roth_ira": "Roth IRA",
    "smart_portfolio": "Smart Portfolio",
}

# 2026 Baseline YTD anchors (if December 31, 2025 statement is missing)
PORTFOLIO_ANCHORS = {
    "personal_brokerage": 29246.92,
    "roth_ira": 48161.20,
    "smart_portfolio": 0.0,
    "combined": 77409.21
}


class PortfolioDomain:
    """Domain module handling ingestion, verification, deduplication, and returns calculation for brokerage portfolios."""

    def __init__(self, db_path: Optional[Path] = None):
        self.manager = MemoryManager(db_path)

    def parse_statement_pdf(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parses a single Apex statement PDF to extract account metadata, balances, cash flows, and holdings."""
        try:
            reader = pypdf.PdfReader(file_path)
            text_by_page = []
            for page in reader.pages:
                text_by_page.append(page.extract_text() or "")
            
            full_text = "\n".join(text_by_page)
            # Normalize dashes/soft hyphens to prevent split strings
            full_text_normalized = full_text.replace("\xad", "-").replace("­", "-")

            # 1. Identify Account Number
            acct_match = re.search(r'ACCOUNT NUMBER\s*([7S6][A-Z0-9]{2}-?\d{5}-?\d{2})', full_text_normalized, re.IGNORECASE)
            if not acct_match:
                # No account number detected; likely a disclosure-only document
                return None
            
            raw_acct = acct_match.group(1).strip()
            clean_acct = raw_acct.replace("-", "").replace(" ", "")
            
            account_key = None
            for key_acct, key_name in ACCOUNT_MAP.items():
                if key_acct in clean_acct:
                    account_key = key_name
                    break
            
            if not account_key:
                # Account not in tracking map
                return None

            # 2. Extract Statement Period Dates
            period_match = re.search(r'([A-Za-z]+\s+\d{1,2},\s+20\d{2})\s*-\s*([A-Za-z]+\s+\d{1,2},\s+20\d{2})', full_text_normalized)
            if not period_match:
                return None
            
            start_str = period_match.group(1).strip()
            end_str = period_match.group(2).strip()
            
            # Format dates to standard YYYY-MM-DD
            try:
                period_start = datetime.strptime(start_str, "%B %d, %Y").strftime("%Y-%m-%d")
            except ValueError:
                try:
                    period_start = datetime.strptime(start_str, "%b %d, %Y").strftime("%Y-%m-%d")
                except ValueError:
                    period_start = start_str
            
            try:
                period_end = datetime.strptime(end_str, "%B %d, %Y").strftime("%Y-%m-%d")
            except ValueError:
                try:
                    period_end = datetime.strptime(end_str, "%b %d, %Y").strftime("%Y-%m-%d")
                except ValueError:
                    period_end = end_str

            # 3. Extract Opening and Closing Balances
            # Search line by line for: Net Account Balance, Total Priced Portfolio, Total Equity Holdings
            opening_cash = 0.0
            closing_cash = 0.0
            opening_securities = 0.0
            closing_securities = 0.0
            opening_total = 0.0
            closing_total = 0.0

            lines = full_text_normalized.split("\n")
            for line in lines:
                line_strip = line.strip()
                if "NET ACCOUNT BALANCE" in line_strip:
                    nums = re.findall(r'[\d,]+\.\d{2}', line_strip)
                    if len(nums) == 2:
                        opening_cash = float(nums[0].replace(",", ""))
                        closing_cash = float(nums[1].replace(",", ""))
                    elif len(nums) == 1:
                        closing_cash = float(nums[0].replace(",", ""))
                elif "TOTAL PRICED PORTFOLIO" in line_strip:
                    nums = re.findall(r'[\d,]+\.\d{2}', line_strip)
                    if len(nums) == 2:
                        opening_securities = float(nums[0].replace(",", ""))
                        closing_securities = float(nums[1].replace(",", ""))
                    elif len(nums) == 1:
                        closing_securities = float(nums[0].replace(",", ""))
                elif "Total Equity Holdings" in line_strip:
                    nums = re.findall(r'[\d,]+\.\d{2}', line_strip)
                    if len(nums) == 2:
                        opening_total = float(nums[0].replace(",", ""))
                        closing_total = float(nums[1].replace(",", ""))
                    elif len(nums) == 1:
                        closing_total = float(nums[0].replace(",", ""))

            # Calculate total fallbacks
            if opening_total == 0.0:
                opening_total = opening_cash + opening_securities
            if closing_total == 0.0:
                closing_total = closing_cash + closing_securities

            # 4. Extract Positions / Holdings Snapshot
            positions = []
            # High-precision regex pattern verified via scan diagnostics
            position_pattern = r'\b([A-Z0-9./#]{1,8})\s+([CMS])\s+([\d,]+\.?\d*)\s+\x24?([\d,]+\.\d{2,4})\s+\x24?([\d,]+\.\d{2})\b'
            
            for page_idx, page_text in enumerate(text_by_page):
                norm_text = page_text.replace("\xad", "-").replace("­", "-")
                # Look for pages with portfolio holdings to minimize noise
                if any(m in norm_text for m in ["EQUI T I E S / OPT I ON S", "Total Equities", "PORTFOLIO SUMMARY", "MUTUAL FUNDS"]):
                    matches = re.findall(position_pattern, norm_text)
                    for m in matches:
                        positions.append({
                            "ticker": m[0],
                            "quantity": float(m[2].replace(",", "")),
                            "price": float(m[3].replace(",", "")),
                            "market_value": float(m[4].replace(",", "")),
                            "percent_of_account": None  # Calculate later relative to total portfolio
                        })

            # Calculate relative percentage for positions
            if closing_total > 0.0:
                for p in positions:
                    p["percent_of_account"] = round((p["market_value"] / closing_total) * 100, 3)

            # 5. Extract Transaction Details / Cash Flows
            raw_txs = []
            for page_text in text_by_page:
                norm_text = page_text.replace("\xad", "-").replace("­", "-")
                if "TRANSACTION DATE" in norm_text or "BANK ACTIVITY" in norm_text:
                    for line in norm_text.split("\n"):
                        if "SWEEP" in line.upper():
                            continue
                        # A transaction line MUST contain a date pattern like MM/DD/YY or MM/DD/YYYY
                        date_match = re.search(r'\b(\d{2}/\d{2}/\d{2,4})\b', line)
                        if not date_match:
                            continue
                        
                        date_str = date_match.group(1)
                        line_upper = line.upper()
                        
                        is_dep = any(k in line_upper for k in ["ACH DEPOSIT", "CONTRIBUTION", "Credit from STASH CAPITAL", "PROMOTIONAL CREDIT"])
                        is_wth = any(k in line_upper for k in ["ACH DISBURSEMENT", "REVERSE ACH DEPOSIT", "REVERSE ACH"])
                        is_inc = any(k in line_upper for k in ["DIVIDEND", "INTEREST", "LENDING REBATE"])
                        
                        if is_dep or is_wth or is_inc:
                            nums = re.findall(r'\-?\x24?[\d,]+\.\d{2}', line)
                            if nums:
                                try:
                                    val = float(nums[-1].replace(chr(36), "").replace(",", ""))
                                    raw_txs.append({
                                        "date": date_str,
                                        "amount": val,
                                        "is_dep": is_dep,
                                        "is_wth": is_wth,
                                        "is_inc": is_inc,
                                        "desc": line
                                    })
                                except ValueError:
                                    pass

            # Deduplicate transactions on the same date with the same amount
            # If one is labeled CONTRIBUTION and one is labeled ACH DEPOSIT/ACH, keep the ACH one
            grouped_txs: Dict[Tuple[str, float], List[dict]] = {}
            for tx in raw_txs:
                key = (tx["date"], abs(tx["amount"]))
                grouped_txs.setdefault(key, []).append(tx)
                
            deduped_txs = []
            for key, tx_list in grouped_txs.items():
                if len(tx_list) > 1:
                    ach_lines = [t for t in tx_list if "ACH" in t["desc"].upper() or "DEPOSIT" in t["desc"].upper()]
                    if ach_lines:
                        deduped_txs.append(ach_lines[0])
                    else:
                        deduped_txs.append(tx_list[0])
                else:
                    deduped_txs.append(tx_list[0])

            deposits = 0.0
            withdrawals = 0.0
            dividends_interest = 0.0

            for tx in deduped_txs:
                val = tx["amount"]
                if tx["is_dep"]:
                    deposits += abs(val)
                elif tx["is_wth"]:
                    withdrawals += abs(val)
                elif tx["is_inc"]:
                    dividends_interest += val

            # Generate statement ID based on file path and parsed metrics to identify uniqueness
            file_size = file_path.stat().st_size
            hash_input = f"{file_path.name}_{file_size}_{account_key}_{period_end}"
            statement_id = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

            return {
                "statement_id": statement_id,
                "account_key": account_key,
                "account_number": clean_acct,
                "period_start": period_start,
                "period_end": period_end,
                "opening_total_value": opening_total,
                "closing_total_value": closing_total,
                "opening_cash": opening_cash,
                "closing_cash": closing_cash,
                "opening_securities": opening_securities,
                "closing_securities": closing_securities,
                "deposits": round(deposits, 2),
                "withdrawals": round(withdrawals, 2),
                "dividends_interest": round(dividends_interest, 2),
                "file_path": str(file_path),
                "positions": positions
            }
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path.name}: {e}")
            return None

    def ingest_statements_from_directory(self, search_dir: Path) -> Dict[str, Any]:
        """Scans directories recursively, parses statement PDFs, resolves duplicate entries, and writes to SQLite."""
        pdf_files = list(search_dir.rglob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files recursively under {search_dir}")

        parsed_records = []
        errors_count = 0

        for path in pdf_files:
            # Skip resumes or receipts
            if "resume" in path.name.lower() or "receipt" in path.name.lower():
                continue
            parsed = self.parse_statement_pdf(path)
            if parsed:
                parsed_records.append(parsed)
            else:
                errors_count += 1

        # Duplicate Statement Resolution Strategy
        # Group statements by (account_key, period_end)
        grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for r in parsed_records:
            key = (r["account_key"], r["period_end"])
            grouped.setdefault(key, []).append(r)

        processed_count = 0
        duplicate_count = 0

        # Ingestion database transactional write
        for (account_key, period_end), statements in grouped.items():
            # If multiple statement files exist for the same month/account, rank them
            canonical_statement = statements[0]
            if len(statements) > 1:
                duplicate_count += len(statements) - 1
                # Scoring heuristic: prefer larger file size and more holdings parsed
                def get_score(s):
                    pos_count = len(s["positions"])
                    file_size = Path(s["file_path"]).stat().st_size
                    has_flows = 1 if (s["deposits"] > 0 or s["withdrawals"] > 0 or s["dividends_interest"] > 0) else 0
                    return pos_count * 10 + has_flows * 5 + (file_size / 500000.0)

                canonical_statement = max(statements, key=get_score)

            # Insert all statements into database, marking the selected canonical statement
            for s in statements:
                s["is_canonical"] = 1 if s["statement_id"] == canonical_statement["statement_id"] else 0
                self.manager.add_portfolio_statement(s)
                processed_count += 1

            # Insert positions associated only with the CANONICAL statement
            for p in canonical_statement["positions"]:
                p["statement_id"] = canonical_statement["statement_id"]
                self.manager.add_portfolio_position(p)

        return {
            "total_scanned": len(pdf_files),
            "total_parsed": len(parsed_records),
            "ingested_statements": processed_count,
            "deduplicated_months": len(grouped),
            "duplicates_flagged": duplicate_count,
            "errors": errors_count
        }

    def get_coverage_matrix(self) -> Dict[str, Dict[str, List[int]]]:
        """Audits coverage status. Returns a matrix mapping each account to years, with lists of active months (1-12)."""
        statements = self.manager.get_portfolio_statements(canonical_only=True)
        
        matrix = {}
        for s in statements:
            acct = s["account_key"]
            # Parse period_end date
            dt = datetime.strptime(s["period_end"], "%Y-%m-%d")
            year_str = str(dt.year)
            month = dt.month
            
            matrix.setdefault(acct, {}).setdefault(year_str, set()).add(month)

        # Convert sets to sorted lists for reporting
        formatted_matrix = {}
        for acct, years in matrix.items():
            formatted_matrix[acct] = {yr: sorted(list(mths)) for yr, mths in years.items()}
            
        return formatted_matrix

    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculates YTD returns, raw monthly performance, and overall CAGR across accounts, checking for data gaps."""
        accounts = list(ACCOUNT_LABELS.keys())
        results = {}

        for acct in accounts:
            statements = self.manager.get_portfolio_statements(account_key=acct, canonical_only=True)
            if not statements:
                continue

            # Inception calculations
            first_stmt = statements[0]
            last_stmt = statements[-1]

            start_val = first_stmt["opening_total_value"]
            end_val = last_stmt["closing_total_value"]

            # Safe guard against zero division
            if start_val == 0.0:
                # Try first non-zero opening or closing balance
                for s in statements:
                    if s["opening_total_value"] > 0.0:
                        start_val = s["opening_total_value"]
                        break
                    elif s["closing_total_value"] > 0.0:
                        start_val = s["closing_total_value"]
                        break

            # Date conversions
            start_date = datetime.strptime(first_stmt["period_start"], "%Y-%m-%d")
            end_date = datetime.strptime(last_stmt["period_end"], "%Y-%m-%d")
            days = (end_date - start_date).days
            years = max(days / 365.25, 0.01)

            # Cumulative raw return
            raw_cum_return = (end_val - start_val) / start_val if start_val > 0.0 else 0.0
            
            # CAGR
            cagr = 0.0
            if start_val > 0.0 and end_val > 0.0:
                cagr = (end_val / start_val) ** (1 / years) - 1

            # YTD Performance (specifically 2026 tracking)
            ytd_2026 = 0.0
            ytd_start_val = 0.0
            # Retrieve December 31, 2025 closing statement
            dec_2025_stmt = None
            for s in statements:
                if s["period_end"] == "2025-12-31":
                    dec_2025_stmt = s
                    break

            if dec_2025_stmt:
                ytd_start_val = dec_2025_stmt["closing_total_value"]
            else:
                # Fallback anchor if Dec 2025 statement is missing from database files
                ytd_start_val = PORTFOLIO_ANCHORS.get(acct, 0.0)

            # Retrieve April/May 2026 or latest statements in 2026
            latest_2026_stmt = None
            for s in reversed(statements):
                if s["period_end"].startswith("2026-"):
                    latest_2026_stmt = s
                    break

            if latest_2026_stmt and ytd_start_val > 0.0:
                ytd_2026 = (latest_2026_stmt["closing_total_value"] - ytd_start_val) / ytd_start_val

            # Cash-flow-adjusted return (TWR) monthly chain
            twr_chain = 1.0
            for s in statements:
                op_val = s["opening_total_value"]
                cl_val = s["closing_total_value"]
                net_cf = s["deposits"] - s["withdrawals"]
                
                # Monthly return calculation adjusted for cash flow
                denominator = op_val + net_cf
                if denominator <= 0.0:
                    denominator = op_val if op_val > 0.0 else 1.0
                
                r_month = (cl_val - op_val - net_cf) / denominator
                twr_chain *= (1.0 + r_month)

            twr_cum = twr_chain - 1.0

            results[acct] = {
                "label": ACCOUNT_LABELS[acct],
                "statements_count": len(statements),
                "period_range": f"{first_stmt['period_start']} to {last_stmt['period_end']}",
                "start_value": start_val,
                "end_value": end_val,
                "raw_cumulative_return": raw_cum_return,
                "cagr": cagr,
                "ytd_2026": ytd_2026,
                "ytd_2026_start_value": ytd_start_val,
                "twr_cumulative_return": twr_cum
            }

        # Calculate Combined Portfolio Returns
        statements = self.manager.get_portfolio_statements(canonical_only=True)
        # Group combined values by month end
        combined_by_month = {}
        for s in statements:
            combined_by_month.setdefault(s["period_end"], []).append(s)

        combined_perf_list = []
        for period_end, stmts in sorted(combined_by_month.items()):
            combined_op = sum(x["opening_total_value"] for x in stmts)
            combined_cl = sum(x["closing_total_value"] for x in stmts)
            combined_dep = sum(x["deposits"] for x in stmts)
            combined_wth = sum(x["withdrawals"] for x in stmts)
            combined_perf_list.append({
                "period_end": period_end,
                "opening_value": combined_op,
                "closing_value": combined_cl,
                "deposits": combined_dep,
                "withdrawals": combined_wth
            })

        if combined_perf_list:
            combined_start = combined_perf_list[0]["opening_value"]
            combined_end = combined_perf_list[-1]["closing_value"]
            
            # CAGR Combined
            combined_start_date = datetime.strptime(combined_perf_list[0]["period_end"], "%Y-%m-%d")
            combined_end_date = datetime.strptime(combined_perf_list[-1]["period_end"], "%Y-%m-%d")
            combined_days = (combined_end_date - combined_start_date).days
            combined_years = max(combined_days / 365.25, 0.01)
            combined_cagr = (combined_end / combined_start) ** (1 / combined_years) - 1 if combined_start > 0.0 else 0.0

            # YTD Combined
            combined_ytd = 0.0
            combined_ytd_start = PORTFOLIO_ANCHORS["combined"]
            # Attempt to sum actual Dec 2025 closes in database
            dec_2025_closes = [x["closing_total_value"] for x in statements if x["period_end"] == "2025-12-31"]
            if len(dec_2025_closes) >= 2:
                combined_ytd_start = sum(dec_2025_closes)

            latest_2026_period = max(x["period_end"] for x in statements if x["period_end"].startswith("2026-"))
            latest_2026_closes = [x["closing_total_value"] for x in statements if x["period_end"] == latest_2026_period]
            
            if latest_2026_closes and combined_ytd_start > 0.0:
                combined_ytd = (sum(latest_2026_closes) - combined_ytd_start) / combined_ytd_start

            # Combined TWR Monthly Chain
            combined_twr_chain = 1.0
            for m in combined_perf_list:
                m_op = m["opening_value"]
                m_cl = m["closing_value"]
                m_cf = m["deposits"] - m["withdrawals"]
                denom = m_op + m_cf
                if denom <= 0.0:
                    denom = m_op if m_op > 0.0 else 1.0
                
                r_month = (m_cl - m_op - m_cf) / denom
                combined_twr_chain *= (1.0 + r_month)

            combined_twr = combined_twr_chain - 1.0

            results["combined"] = {
                "label": "Combined Portfolio",
                "statements_count": len(statements),
                "period_range": f"{combined_perf_list[0]['period_end']} to {combined_perf_list[-1]['period_end']}",
                "start_value": combined_start,
                "end_value": combined_end,
                "raw_cumulative_return": (combined_end - combined_start) / combined_start if combined_start > 0.0 else 0.0,
                "cagr": combined_cagr,
                "ytd_2026": combined_ytd,
                "ytd_2026_start_value": combined_ytd_start,
                "twr_cumulative_return": combined_twr
            }

        return results
