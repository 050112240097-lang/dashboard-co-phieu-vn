# server.py - Flask server + real-time prices + full update with progress
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import pandas as pd
import json
import os
import glob
import threading
import time
import schedule
from datetime import datetime

from roe_analyzer import analyze_roe_full
from deep_valuation import deep_valuation
from hf_compat import is_huggingface, get_port, print_env_info
from watchlist_db import get_all as wl_get_all, add as wl_add, remove as wl_remove, get_symbols as wl_get_symbols, init_db as wl_init

# Load VNStock API key TRUOC KHI goi bat ky API nao
try:
    from config import VNSTOCK_API_KEY
    os.environ['VNSTOCK_API_KEY'] = VNSTOCK_API_KEY
    print(f"  [Server] VNStock key loaded ({len(VNSTOCK_API_KEY)} ky tu)")
except Exception as e:
    print(f"  [Server] Khong load duoc VNStock key: {e}")

app = Flask(__name__, static_folder='.')

# Init watchlist DB
try:
    wl_init()
except Exception as _e:
    print(f"  [Watchlist] Init DB loi: {_e}")
CORS(app)


# ============================================================
# TRẠNG THÁI CẬP NHẬT
# ============================================================
_update_status = {
    'is_running': False,
    'last_run': None,
    'last_success': None,
    'message': 'Chưa chạy',
}

# Lock cho api_reports - tranh scrape song song
_reports_lock = threading.Lock()



def _run_update_background():
    if _update_status['is_running']:
        return
    _update_status['is_running'] = True
    _update_status['last_run'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    _update_status['message'] = 'Đang cập nhật...'

    try:
        from main import run_workflow
        print(f"\n[AUTO] Bat dau cap nhat luc {datetime.now().strftime('%H:%M:%S')}")
        run_workflow()
        _update_status['last_success'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        _update_status['message'] = 'Cập nhật thành công'
        print(f"[AUTO] Cap nhat xong luc {datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        _update_status['message'] = f'Lỗi: {str(e)[:100]}'
        print(f"[AUTO] Loi: {e}")
    finally:
        _update_status['is_running'] = False


def _scheduler_worker():
    schedule.every(15).minutes.do(_run_update_background)
    while True:
        schedule.run_pending()
        time.sleep(30)


_scheduler_thread = threading.Thread(target=_scheduler_worker, daemon=True)
_scheduler_thread.start()


# ============================================================
# AUTO-START WORKFLOW KHI SERVER KHOI DONG
# ============================================================
def _initial_workflow_check():
    """
    Khi server start, cho 10s roi chay workflow lan dau.
    Sau do scheduler moi 15 phut tiep tuc chay.
    Muc dich: user vao web lan dau da co data moi (khong phai cho).
    """
    import time as _time
    _time.sleep(10)
    print("\n[AUTO-START] Chay workflow lan dau sau khi server khoi dong...")
    _run_update_background()


_autostart_thread = threading.Thread(target=_initial_workflow_check, daemon=True)
_autostart_thread.start()




# ============================================================
# CACHE CHO /api/prices (tranh spam API)
# ============================================================
_prices_cache = {'data': None, 'ts': 0}
_PRICES_CACHE_TTL = 60  # giay
_prices_lock = threading.Lock()


# ============================================================
# LOAD DATA
# ============================================================
def load_data():
    data = {'stocks': {}, 'valuations': {}, 'industries': {}}
    try:
        if os.path.exists('stock_data.xlsx'):
            df = pd.read_excel('stock_data.xlsx')
            for _, row in df.iterrows():
                sym = str(row['symbol'])
                data['stocks'][sym] = {
                    'symbol': sym,
                    'exchange': str(row.get('exchange', '')),
                    'close': float(row['close']) if pd.notna(row.get('close')) else None,
                    'pct': float(row['pct']) if pd.notna(row.get('pct')) else 0,
                    'volume': int(row['volume']) if pd.notna(row.get('volume')) else 0,
                    'reference': float(row['reference']) if pd.notna(row.get('reference')) else None,
                    'high': float(row['high']) if pd.notna(row.get('high')) else None,
                    'low': float(row['low']) if pd.notna(row.get('low')) else None,
                    'open': float(row['open']) if pd.notna(row.get('open')) else None,
                }
    except Exception as e:
        print(f"  [load_data] Loi doc Excel: {e}")
    try:
        if os.path.exists('valuation_cache.json'):
            with open('valuation_cache.json', 'r', encoding='utf-8') as f:
                data['valuations'] = json.load(f).get('ratios', {})
    except Exception:
        pass
    try:
        if os.path.exists('industries_cache.json'):
            with open('industries_cache.json', 'r', encoding='utf-8') as f:
                data['industries'] = json.load(f).get('items', {})
    except Exception:
        pass
    return data


# ============================================================
# API ENDPOINTS
# ============================================================
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/api/refresh', methods=['POST', 'GET'])
def api_refresh():
    if _update_status['is_running']:
        return jsonify({'status': 'running', **_update_status})
    thread = threading.Thread(target=_run_update_background, daemon=True)
    thread.start()
    return jsonify({
        'status': 'started',
        'message': 'Da bat dau cap nhat toan bo.',
        **_update_status
    })


@app.route('/api/status')
def api_status():
    result = dict(_update_status)
    try:
        from main import WORKFLOW_PROGRESS
        result.update(WORKFLOW_PROGRESS)
    except Exception:
        pass
    return jsonify(result)


@app.route('/api/last-update')
def api_last_update():
    try:
        if os.path.exists('index.html'):
            mtime = os.path.getmtime('index.html')
            return jsonify({
                'last_update': datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M:%S'),
                'timestamp': mtime
            })
    except Exception:
        pass
    return jsonify({'last_update': None, 'timestamp': 0})


@app.route('/api/prices')
def api_prices():
    """Fetch gia real-time (co cache 20s, khong block)."""
    # Cache check
    now = time.time()
    if _prices_cache['data'] and (now - _prices_cache['ts']) < _PRICES_CACHE_TTL:
        cached = _prices_cache['data']
        return jsonify({
            'status': 'ok_cached',
            'stocks': cached['stocks'],
            'total': cached['total'],
            'elapsed_seconds': 0,
            'updated': cached['updated'],
            'cached': True,
        })

    # Neu dang co request khac fetch -> tra cache cu (du het TTL)
    if not _prices_lock.acquire(blocking=False):
        if _prices_cache['data']:
            cached = _prices_cache['data']
            return jsonify({
                'status': 'ok_cached',
                'stocks': cached['stocks'],
                'total': cached['total'],
                'elapsed_seconds': 0,
                'updated': cached['updated'],
                'cached': True,
                'note': 'Dang fetch, tra cache cu',
            })
        return jsonify({'status': 'fetching', 'stocks': [], 'total': 0}), 202

    try:
        from vnstock import Trading, Listing
        from config import DATA_SOURCE, LISTING_SOURCE

        start = time.time()
        print(f"\n[PRICES] Fetch gia real-time luc {datetime.now().strftime('%H:%M:%S')}")

        listing = Listing(source=LISTING_SOURCE)
        df_list = listing.all_symbols()
        code_col = next((c for c in ['symbol', 'ticker', 'code'] if c in df_list.columns), None)
        symbols = sorted([str(s).strip().upper() for s in df_list[code_col].dropna().unique()])
        print(f"[PRICES] {len(symbols)} ma")

        trading = Trading(source=DATA_SOURCE)
        BATCH_SIZE = 50
        all_rows = []

        for i in range(0, len(symbols), BATCH_SIZE):
            batch = symbols[i:i + BATCH_SIZE]
            try:
                df = trading.price_board(batch)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        try:
                            sym = str(row.get('symbol', '')).strip().upper()
                            if not sym:
                                continue

                            def clean(v, default=None):
                                if v is None:
                                    return default
                                try:
                                    if pd.isna(v):
                                        return default
                                except Exception:
                                    pass
                                return v

                            close = clean(row.get('close_price'))
                            ref = clean(row.get('reference_price'))
                            ceiling = clean(row.get('ceiling_price'))
                            floor = clean(row.get('floor_price'))
                            change = clean(row.get('price_change', 0), 0)
                            pct = clean(row.get('percent_change', 0), 0)
                            f_buy = clean(row.get('foreign_buy_volume', 0), 0) or 0
                            f_sell = clean(row.get('foreign_sell_volume', 0), 0) or 0

                            if (not change or not pct) and ref and close:
                                try:
                                    change = float(close) - float(ref)
                                    pct = (change / float(ref)) * 100 if float(ref) > 0 else 0
                                except Exception:
                                    pass

                            def to_num(v):
                                try:
                                    if v is None or pd.isna(v):
                                        return None
                                    return float(v)
                                except Exception:
                                    return None

                            def to_int(v):
                                try:
                                    if v is None or pd.isna(v):
                                        return 0
                                    return int(v)
                                except Exception:
                                    return 0

                            t = clean(row.get('time'))
                            time_str = None
                            if t:
                                try:
                                    time_str = datetime.fromtimestamp(t / 1000).strftime('%d/%m/%Y %H:%M:%S')
                                except Exception:
                                    pass

                            all_rows.append({
                                'symbol': sym,
                                'exchange': str(row.get('exchange', '') or ''),
                                'ceiling': to_num(ceiling),
                                'floor': to_num(floor),
                                'reference': to_num(ref),
                                'close': to_num(close),
                                'open': to_num(row.get('open_price')),
                                'high': to_num(row.get('high_price')),
                                'low': to_num(row.get('low_price')),
                                'volume': to_int(row.get('volume_accumulated')),
                                'change': round(float(change), 2) if change else 0,
                                'pct': round(float(pct), 2) if pct else 0,
                                'foreign_buy': int(f_buy),
                                'foreign_sell': int(f_sell),
                                'foreign_net': int(f_buy - f_sell),
                                'bid_price_1': to_num(row.get('bid_price_1')),
                                'bid_vol_1': to_int(row.get('bid_vol_1')),
                                'bid_price_2': to_num(row.get('bid_price_2')),
                                'bid_vol_2': to_int(row.get('bid_vol_2')),
                                'bid_price_3': to_num(row.get('bid_price_3')),
                                'bid_vol_3': to_int(row.get('bid_vol_3')),
                                'ask_price_1': to_num(row.get('ask_price_1')),
                                'ask_vol_1': to_int(row.get('ask_vol_1')),
                                'ask_price_2': to_num(row.get('ask_price_2')),
                                'ask_vol_2': to_int(row.get('ask_vol_2')),
                                'ask_price_3': to_num(row.get('ask_price_3')),
                                'ask_vol_3': to_int(row.get('ask_vol_3')),
                                'time': time_str,
                            })
                        except Exception:
                            continue
            except Exception as e:
                print(f"[PRICES] Batch loi: {str(e)[:60]}")
            time.sleep(0.3)

        elapsed = time.time() - start
        print(f"[PRICES] Xong {len(all_rows)} ma trong {elapsed:.1f}s")

        updated_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        # Luu cache
        _prices_cache['data'] = {
            'stocks': all_rows,
            'total': len(all_rows),
            'updated': updated_str,
        }
        _prices_cache['ts'] = time.time()

        return jsonify({
            'status': 'ok',
            'stocks': all_rows,
            'total': len(all_rows),
            'elapsed_seconds': round(elapsed, 1),
            'updated': updated_str,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Tra cache cu neu co
        if _prices_cache['data']:
            cached = _prices_cache['data']
            return jsonify({
                'status': 'ok_cached',
                'stocks': cached['stocks'],
                'total': cached['total'],
                'updated': cached['updated'],
                'cached': True,
                'error_note': str(e)[:100],
            })
        return jsonify({'error': str(e)[:200], 'stocks': []}), 500
    finally:
        try:
            _prices_lock.release()
        except Exception:
            pass


@app.route('/api/reports')
def api_reports():
    try:
        from ssi_reports import fetch_ssi_reports
        force = request.args.get('force', '0') == '1'

        # Lock: neu dang co request scrape chay -> tra cache luon
        if not _reports_lock.acquire(blocking=False):
            print("  [Reports] Dang scrape, tra cache cu")
            try:
                import json as _json
                if os.path.exists('reports_cache.json'):
                    with open('reports_cache.json', 'r', encoding='utf-8') as f:
                        cached = _json.load(f)
                    return jsonify({
                        'reports': cached.get('reports', []),
                        'total': len(cached.get('reports', [])),
                        'updated': cached.get('_updated', ''),
                        'note': 'Dang scrape, tra cache cu',
                    })
            except Exception:
                pass
            return jsonify({'reports': [], 'total': 0, 'updated': '', 'note': 'Dang scrape'}), 202

        try:
            reports = fetch_ssi_reports(force_refresh=force)
            return jsonify({
                'reports': reports,
                'total': len(reports),
                'updated': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            })
        finally:
            _reports_lock.release()
    except Exception as e:
        return jsonify({'error': str(e), 'reports': []}), 500


@app.route('/api/pdfs')
def list_pdfs():
    try:
        pdfs = []
        for f in glob.glob('*.pdf'):
            stat = os.stat(f)
            pdfs.append({
                'filename': f,
                'size': stat.st_size,
                'size_kb': round(stat.st_size / 1024, 1),
                'mtime': stat.st_mtime,
                'modified': pd.Timestamp(stat.st_mtime, unit='s').strftime('%d/%m/%Y %H:%M'),
            })
        pdfs.sort(key=lambda x: x['mtime'], reverse=True)
        return jsonify({'pdfs': pdfs, 'total': len(pdfs)})
    except Exception as e:
        return jsonify({'error': str(e), 'pdfs': []}), 500


@app.route('/pdfs/<path:filename>')
def serve_pdf(filename):
    if not filename.endswith('.pdf'):
        return jsonify({'error': 'Chi cho phep file PDF'}), 400
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Ten file khong hop le'}), 400
    filepath = os.path.join(os.getcwd(), filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File khong ton tai'}), 404
    return send_file(filepath, mimetype='application/pdf')


@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        req = request.get_json()
        symbol = (req.get('symbol') or '').upper().strip()
        question = (req.get('question') or '').strip()
        if not symbol:
            return jsonify({'error': 'Vui long nhap ma co phieu'}), 400
        data = load_data()
        stock = data['stocks'].get(symbol)
        if not stock:
            return jsonify({'error': f'Khong tim thay ma {symbol}'}), 404
        valuation = data['valuations'].get(symbol, {})
        industry = data['industries'].get(symbol, {})
        from ai_reporter import generate_stock_report
        result = generate_stock_report(stock, valuation, industry, question or None)
        return jsonify({
            'symbol': symbol,
            'stock': stock,
            'valuation': valuation,
            'industry': industry,
            'report': result.get('report'),
            'error': result.get('error'),
        })
    except Exception as e:
        return jsonify({'error': f'Loi server: {str(e)[:200]}'}), 500


@app.route('/api/deep-analyze', methods=['POST'])
def deep_analyze():
    """
    Phan tich chuyen sau: dinh gia + Dupont + ROE toan nganh + AI report.
    """
    try:
        req = request.get_json()
        symbol = (req.get('symbol') or '').upper().strip()
        question = (req.get('question') or '').strip()
        if not symbol:
            return jsonify({'error': 'Vui long nhap ma co phieu'}), 400

        data = load_data()
        stock = data['stocks'].get(symbol)

        if not stock:
            try:
                from vnstock import Trading
                from config import DATA_SOURCE
                trading = Trading(source=DATA_SOURCE)
                df = trading.price_board([symbol])
                if df is not None and not df.empty:
                    row = df.iloc[0]
                    close_val = row.get('close_price') or row.get('reference_price')
                    ref_val = row.get('reference_price')
                    pct_val = row.get('percent_change') or 0
                    try:
                        close_val = float(close_val) if close_val else 0
                        ref_val = float(ref_val) if ref_val else 0
                        pct_val = float(pct_val) if pct_val else 0
                    except Exception:
                        close_val, ref_val, pct_val = 0, 0, 0
                    stock = {
                        'symbol': symbol,
                        'exchange': str(row.get('exchange', '')),
                        'close': close_val,
                        'reference': ref_val,
                        'pct': pct_val,
                        'volume': 0,
                    }
            except Exception as e:
                print(f"  [deep-analyze] Fallback fetch loi: {e}")

        if not stock:
            return jsonify({'error': f'Khong tim thay ma {symbol}'}), 404

        valuation = data['valuations'].get(symbol, {})
        industry = data['industries'].get(symbol, {})
        industry_group = industry.get('group')

        if not industry_group:
            try:
                from industry_classifier import MANUAL_MAP
                fb_group = MANUAL_MAP.get(symbol)
                if fb_group:
                    industry_group = fb_group
                    industry = {'symbol': symbol, 'icb': None, 'group': fb_group}
            except Exception:
                pass

        if not valuation:
            try:
                from valuation_analyzer import fetch_ratio
                close_price = stock.get('close') or 0
                valuation = fetch_ratio(symbol, close_price)
            except Exception as e:
                print(f"  [deep-analyze] Fallback valuation loi: {e}")
                valuation = {}

        industry_roe_data = {}
        if industry_group:
            try:
                from industry_roe_full import compute_industry_roe_full
                full_data = compute_industry_roe_full(industry_group)
                if full_data:
                    if full_data.get('median_roe') is not None:
                        full_data['avg_roe_original'] = full_data['avg_roe']
                        full_data['avg_roe'] = full_data['median_roe']
                        full_data['using'] = 'median'
                    industry_roe_data[industry_group] = full_data
                    print(f"  [deep-analyze] ROE nganh {industry_group}: "
                          f"median={full_data['avg_roe']}%, n={full_data['count']}, "
                          f"source={full_data.get('source')}")
            except Exception as e:
                print(f"  [deep-analyze] Loi tinh ROE nganh: {e}")

        close_price = stock.get('close') or 0


        # Tinh trade plan
        trade_plan = None
        try:
            from technical_analyzer import compute_ma_rsi
            _ta = compute_ma_rsi(symbol)
            trade_plan = _ta.get('trade_plan')
            if trade_plan:
                print(f"  [deep-analyze] Trade plan OK: R:R={trade_plan.get('rr_ratio')}")
        except Exception as e:
            print(f"  [deep-analyze] Loi trade plan: {e}")

        # Cham diem tong hop
        scoring_result = None
        try:
            from scoring import load_cache as score_load, compute_score
            all_scores = score_load()
            scoring_result = all_scores.get(symbol)
            if not scoring_result:
                # Fallback: tinh lai cho ma nay
                _industry = industry_group or 'Khác'
                _ind_roe = industry_roe_data.get(_industry, {})
                scoring_result = compute_score(
                    symbol, valuation, {}, _industry, industry_roe_data,
                    None, None, close_price
                )
            if scoring_result:
                print(f"  [deep-analyze] Scoring: {scoring_result.get('label_vn')} (total={scoring_result.get('total')})")
        except Exception as e:
            print(f"  [deep-analyze] Loi scoring: {e}")

        # Chi so rui ro
        risk_result = None
        try:
            from risk_metrics import load_cache as risk_load, compute_risk, _fetch_benchmark
            all_risk = risk_load()
            risk_result = all_risk.get(symbol)
            if not risk_result or 'error' in risk_result:
                _bench = _fetch_benchmark()
                risk_result = compute_risk(symbol, _bench)
            if risk_result and 'error' not in risk_result:
                print(f"  [deep-analyze] Risk OK: beta={risk_result.get('beta')}, sigma={risk_result.get('sigma_annual')}")
        except Exception as e:
            print(f"  [deep-analyze] Loi risk: {e}")

        _dupont_for_compare = None
        try:
            from roe_analyzer import compute_dupont
            _dupont_for_compare = compute_dupont(symbol)
        except Exception as e:
            print(f"  [deep-analyze] Loi compute_dupont: {e}")

        _roe_for_compare = valuation.get('roe')
        if _dupont_for_compare and not _dupont_for_compare.get('error'):
            _roe_for_compare = round(_dupont_for_compare.get('roe_3layer', 0) * 100, 2)
            print(f"  [deep-analyze] Dung ROE Dupont: {_roe_for_compare}%")

        roe_result = analyze_roe_full(
            symbol,
            _roe_for_compare,
            industry_group,
            industry_roe_data
        )

        deep_val = deep_valuation(
            symbol,
            close_price,
            valuation,
            industry_pe_avg=None,
            industry_pb_avg=None,
        )

        valuation_for_ai = deep_val.get('valuation_used') or valuation

        from ai_reporter import generate_deep_analysis_report
        ai_result = generate_deep_analysis_report(
            symbol, stock, valuation_for_ai, industry,
            roe_result, deep_val, question or None
        )

        return jsonify({
            'symbol': symbol,
            'stock': stock,
            'valuation': valuation_for_ai,
            'industry': industry,
            'roe_analysis': roe_result,
            'deep_valuation': deep_val,
            'risk': risk_result,
            'scoring': scoring_result,
            'trade_plan': trade_plan,
            'report': ai_result.get('report'),
            'error': ai_result.get('error'),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Loi server: {str(e)[:200]}'}), 500




@app.route('/api/chart/<symbol>')
def api_chart(symbol):
    """Tra ve chart base64 cho 1 ma."""
    try:
        symbol = symbol.upper().strip()
        from chart_generator import generate_chart_base64
        b64, info = generate_chart_base64(symbol, length=90)
        if not b64:
            return jsonify({'error': info.get('error', 'Khong tao duoc chart'), 'symbol': symbol}), 500
        return jsonify({
            'symbol': symbol,
            'image': 'data:image/png;base64,' + b64,
            'info': info,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)[:200]}), 500




# ============================================================
# WATCHLIST API
# ============================================================
@app.route('/api/watchlist', methods=['GET'])
def api_watchlist_get():
    try:
        items = wl_get_all()
        return jsonify({'items': items, 'total': len(items)})
    except Exception as e:
        return jsonify({'error': str(e)[:200], 'items': []}), 500


@app.route('/api/watchlist', methods=['POST'])
def api_watchlist_add():
    try:
        req = request.get_json() or {}
        symbol = (req.get('symbol') or '').upper().strip()
        note = req.get('note', '')
        target = req.get('target_price')
        stop = req.get('stop_price')
        if not symbol:
            return jsonify({'error': 'Thieu symbol'}), 400
        result = wl_add(symbol, note, target, stop)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 500


@app.route('/api/watchlist/<symbol>', methods=['DELETE'])
def api_watchlist_remove(symbol):
    try:
        result = wl_remove(symbol)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 500


@app.route('/api/watchlist/check/<symbol>', methods=['GET'])
def api_watchlist_check(symbol):
    try:
        from watchlist_db import is_in_watchlist
        return jsonify({'symbol': symbol.upper(), 'in_watchlist': is_in_watchlist(symbol)})
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 500




@app.route('/api/ctck/<symbol>')
def api_ctck(symbol):
    """Tra ve khuyen nghi CTCK cho 1 ma."""
    try:
        symbol = symbol.upper().strip()
        from ctck_analyzer import load_cache
        data = load_cache()
        info = data.get(symbol)
        if not info:
            return jsonify({'symbol': symbol, 'found': False, 'recommendations': []})
        return jsonify({'symbol': symbol, 'found': True, **info})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)[:200]}), 500


@app.route('/api/ctck')
def api_ctck_all():
    """Tra ve tat ca cac ma co khuyen nghi CTCK."""
    try:
        from ctck_analyzer import load_cache
        data = load_cache()
        # Rut gon: chi tra ve summary
        summary = []
        for sym, info in data.items():
            summary.append({
                'symbol': sym,
                'total_reports': info.get('total_reports', 0),
                'buy_count': info.get('buy_count', 0),
                'hold_count': info.get('hold_count', 0),
                'sell_count': info.get('sell_count', 0),
                'avg_target': info.get('avg_target'),
                'max_target': info.get('max_target'),
                'min_target': info.get('min_target'),
            })
        # Sap xep theo so luong bao cao
        summary.sort(key=lambda x: x['total_reports'], reverse=True)
        return jsonify({'items': summary, 'total': len(summary)})
    except Exception as e:
        return jsonify({'error': str(e)[:200], 'items': []}), 500




@app.route('/api/scores')
def api_scores():
    """Tra ve diem cham cho tat ca cac ma."""
    try:
        from scoring import load_cache
        data = load_cache()
        # Rut gon: chi tra ve summary
        summary = {}
        for sym, s in data.items():
            summary[sym] = {
                'total': s.get('total'),
                'label': s.get('label'),
                'label_vn': s.get('label_vn'),
            }
        return jsonify({'items': summary, 'total': len(summary)})
    except Exception as e:
        return jsonify({'error': str(e)[:200], 'items': {}}), 500


@app.route('/api/score/<symbol>')
def api_score_one(symbol):
    """Tra ve diem cham chi tiet cho 1 ma."""
    try:
        from scoring import load_cache
        data = load_cache()
        info = data.get(symbol.upper())
        if not info:
            return jsonify({'symbol': symbol.upper(), 'found': False})
        return jsonify({'symbol': symbol.upper(), 'found': True, **info})
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 500




@app.route('/api/risk/<symbol>')
def api_risk(symbol):
    """Tra ve chi so rui ro cho 1 ma."""
    try:
        symbol = symbol.upper().strip()
        from risk_metrics import load_cache, compute_risk, _fetch_benchmark
        data = load_cache()
        info = data.get(symbol)
        if not info or 'error' in info:
            bench = _fetch_benchmark()
            info = compute_risk(symbol, bench)
        if not info or 'error' in info:
            return jsonify({'symbol': symbol, 'found': False, 'error': (info or {}).get('error')})
        return jsonify({'symbol': symbol, 'found': True, **info})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)[:200]}), 500


@app.route('/api/risk/compare/<sym1>/<sym2>')
def api_risk_compare(sym1, sym2):
    """So sanh rui ro 2 ma + correlation."""
    try:
        sym1 = sym1.upper().strip()
        sym2 = sym2.upper().strip()
        from risk_metrics import load_cache, compute_risk, _fetch_benchmark, correlation
        cache = load_cache()
        bench = _fetch_benchmark()

        r1 = cache.get(sym1)
        if not r1 or 'error' in r1:
            r1 = compute_risk(sym1, bench)
        r2 = cache.get(sym2)
        if not r2 or 'error' in r2:
            r2 = compute_risk(sym2, bench)

        corr = correlation(sym1, sym2)

        return jsonify({
            'sym1': sym1,
            'sym2': sym2,
            'data1': r1,
            'data2': r2,
            'correlation': corr,
        })
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 500




# ============================================================
# COMPARE API
# ============================================================
@app.route('/api/compare/<sym1>/<sym2>')
def api_compare(sym1, sym2):
    """
    So sanh 2 ma cung nganh.
    Tra ve chi so rui ro 2 ma, correlation, chart base64.
    """
    try:
        sym1 = sym1.upper().strip()
        sym2 = sym2.upper().strip()

        from compare_analyzer import compare_two
        result = compare_two(sym1, sym2)

        if result.get('error'):
            return jsonify({'error': result['error']}), 400

        # Bo sung them thong tin tu cac cache khac
        try:
            from valuation_analyzer import load_cache as val_load
            val = val_load()
            result['valuation1'] = val.get(sym1, {})
            result['valuation2'] = val.get(sym2, {})
        except Exception:
            pass

        try:
            from industry_classifier import MANUAL_MAP
            result['industry1'] = MANUAL_MAP.get(sym1, 'Khác')
            result['industry2'] = MANUAL_MAP.get(sym2, 'Khác')
        except Exception:
            pass

        try:
            from company_names import get_company_name
            result['name1'] = get_company_name(sym1)
            result['name2'] = get_company_name(sym2)
        except Exception:
            pass

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Loi server: {str(e)[:200]}'}), 500




# ============================================================
# PORTFOLIO OPTIMIZER API
# ============================================================
@app.route('/api/portfolio/optimize', methods=['POST'])
def api_portfolio_optimize():
    """
    Toi uu danh muc Markowitz.
    Body: {
      "holdings": [{"symbol": "FPT", "weight": 35}, ...],
      "rf": 0.033,          // optional
      "max_weight": 1.0,    // optional (0-1)
      "n_mc": 5000          // optional
    }
    """
    try:
        req = request.get_json() or {}
        holdings = req.get('holdings') or []
        if not holdings or len(holdings) < 2:
            return jsonify({'error': 'Can it nhat 2 ma'}), 400

        # Parse holdings
        symbols_weights = []
        for h in holdings:
            sym = (h.get('symbol') or '').upper().strip()
            w = float(h.get('weight') or 0)
            if sym:
                symbols_weights.append((sym, w))

        if len(symbols_weights) < 2:
            return jsonify({'error': 'Can it nhat 2 ma hop le'}), 400

        rf = float(req.get('rf') or 0.033)
        max_w = float(req.get('max_weight') or 1.0)
        n_mc = int(req.get('n_mc') or 5000)

        print(f"  [Portfolio] Optimize: {symbols_weights}, rf={rf}, n_mc={n_mc}")

        from portfolio_optimizer import optimize_portfolio
        result = optimize_portfolio(
            symbols_weights, rf=rf, n_mc=n_mc, max_weight=max_w
        )

        if result.get('error'):
            return jsonify({'error': result['error']}), 400

        # Bo sung ten cong ty
        try:
            from company_names import get_company_name
            result['company_names'] = {s: get_company_name(s) for s in result['symbols']}
        except Exception:
            pass

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Loi server: {str(e)[:200]}'}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("  FLASK SERVER - DASHBOARD CO PHIEU VIET NAM")
    print("=" * 60)
    print(f"  Mo trinh duyet: http://localhost:{get_port(5000)}")
    print("  Auto-refresh: moi 15 phut")
    print("  Nhan Ctrl+C de dung server")
    print("=" * 60)
    # QUAN TRONG: threaded=True de xu ly nhieu request cung luc
    print_env_info()
    _port = get_port(5000)
    app.run(host='0.0.0.0', port=_port, debug=False, threaded=True)