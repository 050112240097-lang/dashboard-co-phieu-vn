# main.py - Dashboard 10 tabs - Full features (FIXED)
import config_bootstrap
import os
import time
import json
import schedule
import pandas as pd
from datetime import datetime

from config import (
    VNSTOCK_API_KEY, EXCEL_FILE, HTML_FILE,
    UPDATE_INTERVAL_MINUTES, VALUATION_LIMIT
)
#os.environ['VNSTOCK_API_KEY'] = VNSTOCK_API_KEY

from data_fetcher import fetch_all_data
from valuation_analyzer import fetch_all_valuations, compute_industry_roe
from industry_classifier import fetch_all_industries
from ai_reporter import generate_market_overview
from ssi_reports import fetch_ssi_reports
from technical_analyzer import fetch_all_technical
from rss_fetcher import fetch_all_news
from pdf_reporter import generate_all_reports
from group_fetcher import fetch_symbol_groups


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Dashboard Cổ Phiếu Việt Nam</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--primary:#1E40AF;--primary-hover:#1E3A8A;--primary-light:#3B82F6;--primary-lighter:#60A5FA;--primary-bg:#EFF6FF;--primary-bg-hover:#DBEAFE;--bg:#F8FAFC;--bg-soft:#F1F5F9;--card:#FFFFFF;--card-hover:#F8FAFC;--overlay:rgba(15,23,42,.5);--text:#0F172A;--text-secondary:#475569;--text-muted:#94A3B8;--border:#E2E8F0;--border-strong:#CBD5E1;--green:#10B981;--green-bg:#ECFDF5;--green-border:#A7F3D0;--red:#EF4444;--red-bg:#FEF2F2;--red-border:#FECACA;--amber:#F59E0B;--amber-bg:#FFFBEB;--amber-border:#FDE68A;--purple:#8B5CF6;--purple-bg:#F5F3FF;--shadow-xs:0 1px 2px rgba(15,23,42,.04);--shadow-sm:0 2px 4px rgba(15,23,42,.06);--shadow-md:0 4px 12px rgba(15,23,42,.08);--shadow-lg:0 12px 32px rgba(15,23,42,.12);--shadow-blue:0 4px 14px rgba(30,64,175,.15);--font-sans:'Inter',sans-serif;--font-mono:'JetBrains Mono',monospace}
body{font-family:var(--font-sans);background:var(--bg);color:var(--text);min-height:100vh;font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased}
header{background:var(--card);border-bottom:1px solid var(--border);padding:0 28px;position:sticky;top:0;z-index:100;box-shadow:var(--shadow-xs)}
.header-in{max-width:100%;height:64px;display:flex;justify-content:space-between;align-items:center;gap:16px}
.logo{display:flex;align-items:center;gap:10px;font-size:17px;font-weight:700;color:var(--primary)}
.logo span:first-child{font-size:24px}
.clock{background:var(--primary-bg);border:1px solid var(--primary-bg-hover);padding:6px 14px;border-radius:8px;color:var(--primary);font-family:var(--font-mono);font-size:12px;font-weight:600;display:flex;align-items:center;gap:8px}
.dot{width:6px;height:6px;background:var(--green);border-radius:50%;box-shadow:0 0 0 3px rgba(16,185,129,.2);animation:blink 1.5s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.4}}
.btn-icon{background:var(--bg);border:1px solid var(--border);color:var(--text-secondary);width:38px;height:38px;border-radius:8px;cursor:pointer;font-size:15px;display:flex;align-items:center;justify-content:center;transition:all .15s}
.btn-icon:hover{background:var(--primary-bg);border-color:var(--primary-lighter);color:var(--primary)}
.tabs{background:var(--card);border-bottom:1px solid var(--border);padding:12px 28px;display:flex;gap:10px;overflow-x:auto;align-items:center}
.tabs::-webkit-scrollbar{height:2px}
.tabs::-webkit-scrollbar-thumb{background:var(--border-strong);border-radius:1px}
.tab{background:transparent;border:1px solid transparent;color:var(--text-secondary);padding:8px 16px;font-size:13px;font-weight:500;cursor:pointer;border-radius:8px;white-space:nowrap;transition:all .15s;display:inline-flex;align-items:center;gap:10px;flex-shrink:0}
.tab:hover{background:var(--primary-bg);color:var(--primary);border-color:var(--primary-bg-hover)}
.tab.active{background:var(--primary);color:white;font-weight:600;border-color:var(--primary);box-shadow:0 4px 14px rgba(30,64,175,.25)}
.wrap{max-width:100%;padding:0 28px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-top:24px}
.stat{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px 22px;position:relative;overflow:hidden;transition:all .2s;box-shadow:var(--shadow-xs)}
.stat::before{content:'';position:absolute;top:0;left:0;width:4px;height:100%;background:var(--primary);border-radius:12px 0 0 12px}
.stat.g::before{background:var(--green)}
.stat.r::before{background:var(--red)}
.stat.y::before{background:var(--amber)}
.stat:hover{border-color:var(--primary-lighter);transform:translateY(-2px);box-shadow:var(--shadow-md)}
.stat-lb{color:var(--text-muted);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px}
.stat-vl{font-size:30px;font-weight:700;letter-spacing:-1px;font-family:var(--font-mono);line-height:1.1}
.sv-b{color:var(--primary)}
.sv-g{color:var(--green)}
.sv-r{color:var(--red)}
.sv-y{color:var(--amber)}
.controls{display:flex;gap:10px;margin-top:20px;flex-wrap:wrap;align-items:center}
.search{flex:1;min-width:240px;position:relative}
.search input{width:100%;padding:11px 16px 11px 42px;background:var(--card);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:13px;outline:none;transition:all .15s;box-shadow:var(--shadow-xs)}
.search input:focus{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-bg)}
.search::before{content:'🔍';position:absolute;left:14px;top:50%;transform:translateY(-50%);font-size:14px;opacity:.5}
select{padding:11px 16px;background:var(--card);border:1px solid var(--border);color:var(--text);border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;outline:none;transition:all .15s;box-shadow:var(--shadow-xs)}
select:hover{border-color:var(--border-strong)}
select:focus{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-bg)}
.table-card{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-top:20px;box-shadow:var(--shadow-sm)}
.table-in{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
thead{background:linear-gradient(180deg,#F8FAFC,#F1F5F9);border-bottom:1px solid var(--border)}
th{color:var(--text-secondary);padding:12px 14px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;white-space:nowrap;position:sticky;top:0;background:#F8FAFC;z-index:10;border-bottom:1px solid var(--border)}
td{padding:10px 14px;border-bottom:1px solid var(--border);font-variant-numeric:tabular-nums}
tr:hover td{background:var(--card-hover)}
tr:last-child td{border-bottom:none}
tr{cursor:pointer;transition:background .1s}
.sym{font-weight:700;color:var(--primary);font-size:13px;letter-spacing:.3px;font-family:var(--font-mono)}
.exch{font-size:10px;color:var(--text-secondary);background:var(--bg-soft);padding:2px 6px;border-radius:4px;margin-left:6px;font-weight:600}
.up{color:var(--green);font-weight:700}
.down{color:var(--red);font-weight:700}
.ref{color:var(--amber);font-weight:700}
.num{text-align:right;font-family:var(--font-mono);font-size:12px;font-weight:500}
.row-up{background:linear-gradient(90deg,transparent,var(--green-bg))}
.row-down{background:linear-gradient(90deg,transparent,var(--red-bg))}
.pagination{display:flex;justify-content:center;gap:6px;margin:24px 0;flex-wrap:wrap;align-items:center}
.pg-btn{min-width:36px;height:36px;padding:0 10px;background:var(--card);border:1px solid var(--border);color:var(--text);border-radius:8px;cursor:pointer;font-size:12px;font-weight:600;font-family:var(--font-mono);transition:all .15s;box-shadow:var(--shadow-xs)}
.pg-btn:hover:not(:disabled){background:var(--primary-bg);border-color:var(--primary-lighter);color:var(--primary)}
.pg-btn.active{background:var(--primary);color:white;border-color:var(--primary);box-shadow:var(--shadow-blue)}
.pg-btn:disabled{opacity:.4;cursor:not-allowed}
.pg-info{color:var(--text-muted);font-size:12px;margin-left:12px;font-weight:500}
.section-title{font-size:18px;font-weight:700;margin:28px 0 16px;display:flex;align-items:center;gap:12px;color:var(--text)}
.section-title::before{content:'';width:4px;height:22px;background:var(--primary);border-radius:2px;box-shadow:var(--shadow-blue)}
.modal-ov{display:none;position:fixed;inset:0;background:var(--overlay);backdrop-filter:blur(4px);z-index:1000;align-items:center;justify-content:center;padding:20px}
.modal-ov.active{display:flex}
.modal{background:var(--card);border-radius:16px;max-width:720px;width:100%;max-height:90vh;overflow-y:auto;border:1px solid var(--border);padding:28px;position:relative;box-shadow:var(--shadow-lg);animation:slideUp .25s}
@keyframes slideUp{from{transform:translateY(20px);opacity:0}to{transform:translateY(0);opacity:1}}
.modal-x{position:absolute;top:16px;right:16px;background:var(--bg);border:1px solid var(--border);color:var(--text-secondary);width:34px;height:34px;border-radius:8px;font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center}
.modal-x:hover{background:var(--red-bg);color:var(--red);border-color:var(--red-border)}
.modal h2{color:var(--primary);margin-bottom:6px;font-size:26px;font-family:var(--font-mono);font-weight:700}
.modal-sub{color:var(--text-secondary);font-size:13px;margin-bottom:22px}
.m-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.m-item{padding:14px;background:var(--bg);border-radius:10px;border:1px solid var(--border);transition:all .15s}
.m-item:hover{background:var(--primary-bg);border-color:var(--primary-bg-hover)}
.m-lb{color:var(--text-muted);font-size:10px;text-transform:uppercase;margin-bottom:6px;font-weight:700;letter-spacing:.6px}
.m-vl{font-size:15px;font-weight:700;font-family:var(--font-mono);color:var(--text)}
.tcard{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px;margin-bottom:12px;transition:all .2s;box-shadow:var(--shadow-xs)}
.tcard:hover{border-color:var(--primary-lighter);box-shadow:var(--shadow-sm)}
.empty{text-align:center;padding:60px 20px;color:var(--text-muted)}
.empty-icon{font-size:52px;margin-bottom:14px;opacity:.4}
.ai-box{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:24px;line-height:1.8;font-size:13px;color:var(--text-secondary);box-shadow:var(--shadow-xs)}
.ai-box h1{font-size:20px;font-weight:700;color:var(--primary);margin:20px 0 12px}
.ai-box h2{font-size:17px;font-weight:700;color:var(--primary);margin:18px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--border)}
.ai-box h3{font-size:15px;font-weight:700;color:var(--primary);margin:16px 0 8px}
.ai-box h4{font-size:14px;font-weight:600;color:var(--text);margin:14px 0 6px}
.ai-box strong{color:var(--text);font-weight:700}
.ai-box em{color:var(--text-secondary);font-style:italic}
.ai-box ul{margin:10px 0;padding-left:22px}
.ai-box li{margin:6px 0;line-height:1.7}
.ai-box hr{border:none;border-top:1px solid var(--border);margin:18px 0}
.ai-box p{margin:10px 0}
.ai-box table.md-table{width:100%;border-collapse:collapse;margin:12px 0;font-size:13px}
.ai-box table.md-table th{background:var(--bg-soft);padding:8px 12px;text-align:left;border:1px solid var(--border);font-weight:700;color:var(--text)}
.ai-box table.md-table td{padding:8px 12px;border:1px solid var(--border);color:var(--text-secondary)}
.ai-box h1{font-size:20px;font-weight:700;color:var(--primary);margin:20px 0 12px}
.ai-box h2{font-size:17px;font-weight:700;color:var(--primary);margin:18px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--border)}
.ai-box h3{font-size:15px;font-weight:700;color:var(--primary);margin:16px 0 8px}
.ai-box h4{font-size:14px;font-weight:600;color:var(--text);margin:14px 0 6px}
.ai-box strong{color:var(--text);font-weight:700}
.ai-box em{color:var(--text-secondary);font-style:italic}
.ai-box ul{margin:10px 0;padding-left:22px}
.ai-box li{margin:6px 0;line-height:1.7}
.ai-box hr{border:none;border-top:1px solid var(--border);margin:18px 0}
.ai-box p{margin:10px 0}
.report-link{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;background:var(--primary);color:white;border-radius:8px;font-size:12px;font-weight:600;text-decoration:none;transition:all .15s;border:1px solid var(--primary);box-shadow:var(--shadow-blue)}
.report-link:hover{background:var(--primary-hover);transform:translateY(-1px)}
.report-link.green{background:var(--green);border-color:var(--green)}
.report-link.green:hover{background:#059669}
.roe-bar{background:var(--bg-soft);border-radius:8px;height:8px;overflow:hidden;margin:10px 0}
.roe-fill{background:linear-gradient(90deg,var(--primary),var(--primary-light));height:100%;border-radius:8px;transition:width .6s}
.news-item{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin-bottom:12px;border-left:4px solid var(--primary);transition:all .2s;box-shadow:var(--shadow-xs)}
.news-item:hover{border-color:var(--primary-lighter);transform:translateX(4px)}
.news-cat{display:inline-block;background:var(--primary-bg);color:var(--primary);padding:4px 10px;border-radius:6px;font-size:10px;font-weight:700;margin-bottom:10px;text-transform:uppercase}
.news-title{font-weight:600;font-size:15px;line-height:1.5;margin-bottom:8px}
.news-title a{color:var(--text);text-decoration:none}
.news-title a:hover{color:var(--primary)}
.news-desc{font-size:13px;color:var(--text-secondary);line-height:1.7;margin-bottom:10px}
.news-date{font-size:11px;color:var(--text-muted);font-family:var(--font-mono);font-weight:500}
.rsi-oversold{color:var(--green);font-weight:700}
.rsi-overbought{color:var(--red);font-weight:700}
.rsi-neutral{color:var(--amber);font-weight:700}
footer{text-align:center;padding:28px;color:var(--text-muted);font-size:11px;border-top:1px solid var(--border);margin-top:48px;background:var(--card)}
.chat-input{padding:12px 16px;background:var(--card);border:1px solid var(--border);border-radius:8px;color:var(--text);outline:none;font-size:13px;transition:all .15s;box-shadow:var(--shadow-xs)}
.chat-input:focus{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-bg)}
.btn-ai{padding:12px 24px;background:var(--primary);color:white;border:1px solid var(--primary);border-radius:8px;font-weight:600;cursor:pointer;font-size:13px;transition:all .15s;box-shadow:var(--shadow-blue);display:inline-flex;align-items:center;gap:6px}
.btn-ai:hover{background:var(--primary-hover);transform:translateY(-1px)}
.badge{display:inline-block;padding:3px 10px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase}
.badge-primary{background:var(--primary-bg);color:var(--primary)}
.toast{position:fixed;bottom:30px;right:30px;background:var(--green);color:white;padding:14px 20px;border-radius:10px;font-weight:600;font-size:13px;box-shadow:0 8px 24px rgba(16,185,129,.4);transform:translateY(100px);opacity:0;transition:all .3s;z-index:2000;pointer-events:none}
.toast.show{transform:translateY(0);opacity:1}
.hidden{display:none!important}
@media(max-width:768px){.wrap,.stats,.tabs,header{padding-left:14px;padding-right:14px}.stat-vl{font-size:22px}.m-grid{grid-template-columns:1fr}}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border-strong);border-radius:5px}
.score-badge{display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;margin-left:6px;white-space:nowrap}
.score-pos{background:var(--green-bg);color:var(--green)}
.score-neu{background:var(--bg-soft);color:var(--text-muted)}
.score-neg{background:var(--red-bg);color:var(--red)}

.wl-btn{background:transparent;border:none;cursor:pointer;font-size:16px;padding:2px 6px;border-radius:6px;transition:all .15s;line-height:1}
.wl-btn:hover{background:var(--amber-bg);transform:scale(1.15)}
.wl-btn.active{color:var(--amber)}
.wl-btn:not(.active){color:var(--text-muted);opacity:.4}
.wl-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:12px;transition:all .15s;box-shadow:var(--shadow-xs);cursor:pointer;border-left:4px solid var(--amber)}
.wl-card:hover{border-color:var(--amber);transform:translateX(4px);box-shadow:var(--shadow-sm)}
.wl-symbol{font-weight:700;color:var(--primary);font-size:18px;font-family:var(--font-mono)}
.wl-meta{display:flex;gap:18px;margin-top:10px;font-size:12px;flex-wrap:wrap}
.wl-meta-item{display:flex;gap:5px}
.wl-meta-label{color:var(--text-muted);font-weight:600}
.wl-meta-value{font-family:var(--font-mono);font-weight:700}
.wl-remove{background:transparent;border:1px solid var(--red-border);color:var(--red);padding:5px 10px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer;transition:all .15s}
.wl-remove:hover{background:var(--red-bg);}

.screener-panel{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px;margin-top:20px;box-shadow:var(--shadow-xs);display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;align-items:end}
.screener-panel .sc-field{display:flex;flex-direction:column;gap:6px}
.screener-panel .sc-label{font-size:11px;color:var(--text-muted);font-weight:700;text-transform:uppercase;letter-spacing:.5px}
.screener-panel .sc-input{padding:9px 12px;background:var(--bg);border:1px solid var(--border);border-radius:8px;font-size:13px;outline:none;transition:all .15s}
.screener-panel .sc-input:focus{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-bg)}
.screener-panel .sc-row{display:flex;gap:6px}
.screener-panel .sc-row .sc-input{flex:1;min-width:0}
.sc-btn{padding:9px 14px;border-radius:8px;font-size:12px;font-weight:700;cursor:pointer;border:1px solid var(--border);background:var(--card);color:var(--text-secondary);transition:all .15s;white-space:nowrap}
.sc-btn:hover{border-color:var(--primary-lighter);color:var(--primary);background:var(--primary-bg)}
.sc-btn.primary{background:var(--primary);color:white;border-color:var(--primary)}
.sc-btn.primary:hover{background:var(--primary-hover)}
.sc-btn.export{background:var(--green);color:white;border-color:var(--green)}
.sc-count{color:var(--text-muted);font-size:12px;font-weight:600;padding:9px 0;grid-column:1/-1;text-align:right}
.sent-badge{display:inline-block;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:700}
.sent-pos{background:var(--green-bg);color:var(--green)}
.sent-neg{background:var(--red-bg);color:var(--red)}
.sent-neu{background:var(--bg-soft);color:var(--text-muted)}
.signal-badge{font-size:10px;font-weight:700;padding:2px 7px;border-radius:5px}

</style>
</head>
<body>

<header>
  <div class="header-in">
    <div class="logo"><span>📊</span><span>Dashboard Cổ Phiếu Việt Nam</span></div>
    <div style="display:flex;gap:10px;align-items:center;">
      <div class="clock"><div class="dot"></div><span id="clock">--:--:--</span></div>
      <button class="btn-icon" onclick="fetchRealtimePrices(false)" id="refreshBtn" title="Cập nhật giá real-time (10s)">🔄</button>
      <button class="btn-icon" onclick="fullRefresh()" id="fullRefreshBtn" title="Cập nhật toàn bộ (5 phút)">⚡</button>
      <button class="btn-icon" onclick="toggleTheme()" id="themeBtn">🌙</button>
    </div>
  </div>
</header>

<div class="tabs">
  <button class="tab active" data-tab="stocks" onclick="switchTab('stocks',this)">📈 Cổ Phiếu</button>
  <button class="tab" data-tab="analysis" onclick="switchTab('analysis',this)">📊 Phân Tích</button>
  <button class="tab" data-tab="ai-report" onclick="switchTab('ai-report',this)">📄 Báo Cáo PDF</button>
  <button class="tab" data-tab="ssi-report" onclick="switchTab('ssi-report',this)">📑 Báo Cáo CTCK</button>
  <button class="tab" data-tab="news" onclick="switchTab('news',this)">📰 Tin Tức</button>
  <button class="tab" data-tab="deep-analyze" onclick="switchTab('deep-analyze',this)">🔬 Phân Tích Sâu</button>
  <button class="tab" data-tab="compare" onclick="switchTab('compare',this)">⚖️ So Sánh</button>
  <button class="tab" data-tab="portfolio" onclick="switchTab('portfolio',this)">💼 Danh Mục</button>
  <button class="tab" data-tab="watchlist" onclick="switchTab('watchlist',this)">⭐ Danh Mục</button>
</div>

<div id="tab-stocks">
  <div class="wrap">
    <div class="stats">
      <div class="stat"><div class="stat-lb">Tổng số mã</div><div class="stat-vl sv-b" id="sTotal">0</div></div>
      <div class="stat g"><div class="stat-lb">Tăng giá</div><div class="stat-vl sv-g" id="sUp">0</div></div>
      <div class="stat r"><div class="stat-lb">Giảm giá</div><div class="stat-vl sv-r" id="sDown">0</div></div>
      <div class="stat y"><div class="stat-lb">Đứng giá</div><div class="stat-vl sv-y" id="sRef">0</div></div>
    </div>
    <div class="controls">
      <div class="search"><input type="text" id="search" placeholder="Tìm mã cổ phiếu..."></div>
      <select id="groupFilter" onchange="renderTable()">
        <option value="">📊 Tất cả nhóm</option>
        <option value="VN30">⭐ VN30</option>
        <option value="VN100">💎 VN100</option>
        <option value="VNDIAMOND">💠 VNDIAMOND</option>
        <option value="HOSE">🏢 HOSE</option>
        <option value="HNX">🏢 HNX</option>
        <option value="UPCOM">🏢 UPCOM</option>
      </select>
      <select id="sortBy" onchange="renderTable()">
        <option value="symbol">Mã (A-Z)</option>
        <option value="pct_desc">Tăng nhiều nhất</option>
        <option value="pct_asc">Giảm nhiều nhất</option>
        <option value="vol_desc">KL nhiều nhất</option>
      </select>
      <select id="perPage" onchange="renderTable()">
        <option value="50">50 mã/trang</option>
        <option value="100">100 mã/trang</option>
        <option value="200">200 mã/trang</option>
        <option value="500">500 mã/trang</option>
      </select>
    </div>
        <div class="screener-panel">
      <div class="sc-field">
        <div class="sc-label">Tìm mã</div>
        <input type="text" id="scSymbol" class="sc-input" placeholder="VD: FPT" oninput="applyScreener()">
      </div>
      <div class="sc-field">
        <div class="sc-label">Ngành</div>
        <select id="scIndustry" class="sc-input" onchange="applyScreener()">
          <option value="">Tất cả ngành</option>
        </select>
      </div>
      <div class="sc-field">
        <div class="sc-label">P/E (min - max)</div>
        <div class="sc-row">
          <input type="number" id="scPeMin" class="sc-input" placeholder="0" oninput="applyScreener()">
          <input type="number" id="scPeMax" class="sc-input" placeholder="30" oninput="applyScreener()">
        </div>
      </div>
      <div class="sc-field">
        <div class="sc-label">ROE tối thiểu (%)</div>
        <input type="number" id="scRoeMin" class="sc-input" placeholder="VD: 15" oninput="applyScreener()">
      </div>
      <div class="sc-field">
        <div class="sc-label">Tin tức</div>
        <select id="scSentiment" class="sc-input" onchange="applyScreener()">
          <option value="">Tất cả</option>
          <option value="positive">✅ Tích cực</option>
          <option value="neutral">⚪ Trung lập</option>
          <option value="negative">❌ Tiêu cực</option>
        </select>
      </div>
      <div class="sc-field">
        <div class="sc-label">Kỹ thuật</div>
        <select id="scSignal" class="sc-input" onchange="applyScreener()">
          <option value="">Tất cả</option>
          <option value="Tăng">Tăng</option>
          <option value="Trung tính">Trung tính</option>
          <option value="Giảm">Giảm</option>
        </select>
      </div>
      <div class="sc-field">
        <button class="sc-btn primary" onclick="applyScreener()">🔍 Lọc</button>
      </div>
      <div class="sc-field">
        <button class="sc-btn" onclick="resetScreener()">↺ Xóa lọc</button>
      </div>
      <div class="sc-field">
        <button class="sc-btn export" onclick="exportCSV()">📥 Xuất CSV</button>
      </div>
      <div class="sc-count" id="scCount">Hiển thị 0 mã</div>
    </div>

<div class="table-card">
      <div class="table-in">
        <table>
          <thead><tr>
            <th>Mã</th><th class="num">Trần</th><th class="num">Sàn</th><th class="num">TC</th>
            <th class="num">Giá</th><th class="num">+/-</th><th class="num">%</th>
            <th class="num">KL</th><th class="num">NN ròng</th><th style="text-align:center;">Điểm</th><th>Phiên</th>
          </tr></thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
    </div>
    <div class="pagination" id="pagination"></div>
  </div>
</div>

<div id="tab-analysis" class="hidden">
  <div class="wrap">
    <h2 class="section-title">🎯 Tổng Hợp Phân Tích</h2>
    <div id="analysisList"></div>
  </div>
</div>

<div id="tab-valuation" class="hidden">
  <div class="wrap">
    <h2 class="section-title">💰 Định Giá Chi Tiết Từng Mã</h2>
    <div class="table-card">
      <div class="table-in">
        <table>
          <thead><tr>
            <th>Mã</th><th class="num">P/E</th><th class="num">P/B</th>
            <th class="num">ROE (%)</th><th class="num">ROA (%)</th>
            <th class="num">EPS</th><th class="num">BVPS</th>
          </tr></thead>
          <tbody id="valuationBody"></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<div id="tab-technical" class="hidden">
  <div class="wrap">
    <h2 class="section-title">📉 Chỉ Báo Kỹ Thuật MA & RSI</h2>
    <div class="table-card">
      <div class="table-in">
        <table>
          <thead><tr>
            <th>Mã</th><th class="num">Giá</th><th class="num">MA20</th>
            <th class="num">MA50</th><th class="num">RSI14</th>
            <th style="text-align:center;">Tín hiệu</th>
          </tr></thead>
          <tbody id="technicalBody"></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<div id="tab-industry" class="hidden">
  <div class="wrap">
    <h2 class="section-title">🏢 Phân Loại Ngành ICB</h2>
    <div class="stats" id="industryStats"></div>
    <div id="industryList" style="margin-top:20px;"></div>
  </div>
</div>

<div id="tab-industry-compare" class="hidden">
  <div class="wrap">
    <h2 class="section-title">📊 So Sánh ROE Trung Bình Theo Ngành</h2>
    <div id="industryCompareList"></div>
  </div>
</div>

<div id="tab-ai-report" class="hidden">
  <div class="wrap">
    <h2 class="section-title">📄 Báo Cáo PDF</h2>
    <p style="color:var(--text-secondary);font-size:13px;margin-bottom:20px;">Danh sách báo cáo PDF tự động tạo theo phiên giao dịch.</p>
    <div class="controls" style="padding:0;margin-bottom:20px;">
      <select id="pdfDateFilter" onchange="renderPdfByDate()" style="padding:10px 14px;background:var(--card);border:1px solid var(--border);border-radius:8px;font-size:13px;cursor:pointer;font-weight:500;min-width:200px;">
        <option value="">📅 Tất cả ngày</option>
      </select>
      <button onclick="loadPdfList()" class="btn-ai">🔄 Tải lại</button>
      <span id="pdfCount" style="color:var(--text-muted);font-size:13px;"></span>
    </div>
    <div id="pdfList"><div class="empty"><div class="empty-icon">📄</div><div>Đang tải...</div></div></div>
  </div>
</div>

<div id="tab-news" class="hidden">
  <div class="wrap">
    <h2 class="section-title">📰 Tin Tức CafeF</h2>
    <div class="controls" style="padding:0;margin-bottom:20px;">
      <select id="newsCategoryFilter" onchange="renderNews()"><option value="">Tất cả chuyên mục</option></select>
    </div>
    <div id="newsList"></div>
  </div>
</div>

<div id="tab-ssi-report" class="hidden">
  <div class="wrap">
    <h2 class="section-title">📑 Báo Cáo Từ Các CTCK</h2>
    <div class="controls" style="padding:0;margin-bottom:20px;">
      <button onclick="window._forceReports=false; renderSSIReports()" class="btn-ai">🔄 Tải lại</button>
      <button onclick="window._forceReports=true; renderSSIReports()" class="btn-ai" style="background:var(--amber);border-color:var(--amber);">⚡ Cào lại (30s)</button>
    </div>
    <div id="ssiReportList"></div>
  </div>
</div>


<div id="tab-watchlist" class="hidden">
  <div class="wrap">
    <h2 class="section-title">⭐ Danh Mục Theo Dõi</h2>
    <div class="controls" style="padding:0;margin-bottom:16px;">
      <div class="search" style="max-width:300px;">
        <input type="text" id="wlAddSymbol" placeholder="Nhập mã, VD: FPT" style="text-transform:uppercase;">
      </div>
      <button onclick="addToWatchlist()" class="btn-ai">+ Thêm vào danh mục</button>
      <span id="wlCount" style="color:var(--text-muted);font-size:13px;"></span>
    </div>
    <div id="wlList"></div>
  </div>
</div>


<div id="tab-compare" class="hidden">
  <div class="wrap">
    <h2 class="section-title">⚖️ So Sánh 2 Cổ Phiếu</h2>
    <div class="table-card" style="padding:24px;margin-bottom:20px;">
      <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;">
        <input type="text" id="cmpSym1" class="chat-input" placeholder="Mã 1 (VD: FPT)"
               style="font-size:16px;font-weight:700;text-transform:uppercase;width:150px;text-align:center;">
        <span style="font-size:20px;color:var(--text-muted);font-weight:700;">VS</span>
        <input type="text" id="cmpSym2" class="chat-input" placeholder="Mã 2 (VD: CMG)"
               style="font-size:16px;font-weight:700;text-transform:uppercase;width:150px;text-align:center;">
        <button onclick="runCompare()" class="btn-ai">⚖️ So Sánh</button>
        <span style="color:var(--text-muted);font-size:12px;">Mất ~5-10s lần đầu</span>
      </div>
      <div id="cmpQuick" style="margin-top:12px;display:flex;gap:6px;flex-wrap:wrap;"></div>
    </div>
    <div id="cmpResult" style="min-height:200px;">
      <div class="empty">
        <div class="empty-icon">⚖️</div>
        <div>Nhập 2 mã để so sánh</div>
      </div>
    </div>
  </div>
</div>


<div id="tab-portfolio" class="hidden">
  <div class="wrap">
    <h2 class="section-title">💼 Tối Ưu Danh Mục Markowitz</h2>

    <div class="table-card" style="padding:24px;margin-bottom:20px;">
      <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:end;margin-bottom:16px;">
        <div style="flex:1;min-width:200px;">
          <div class="sc-label" style="margin-bottom:6px;">Mã cổ phiếu (tối đa 12)</div>
          <input type="text" id="pfSymbol" class="chat-input" placeholder="VD: FPT"
                 style="width:100%;text-transform:uppercase;font-weight:700;">
        </div>
        <div style="width:120px;">
          <div class="sc-label" style="margin-bottom:6px;">Tỷ trọng (%)</div>
          <input type="number" id="pfWeight" class="chat-input" placeholder="35" min="0" max="100" style="width:100%;">
        </div>
        <button onclick="addPortfolioItem()" class="btn-ai">+ Thêm</button>
      </div>

      <div id="pfItems" style="min-height:60px;background:var(--bg-soft);padding:12px;border-radius:8px;margin-bottom:16px;">
        <div style="color:var(--text-muted);font-size:12px;text-align:center;padding:10px;">Chưa có mã nào. Thêm 2-12 mã để tối ưu.</div>
      </div>

      <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between;">
        <div style="display:flex;gap:12px;flex-wrap:wrap;">
          <div>
            <div class="sc-label" style="margin-bottom:6px;">Lãi suất phi rủi ro (%/năm)</div>
            <input type="number" id="pfRf" value="3.3" step="0.1" style="padding:8px 12px;background:var(--bg);border:1px solid var(--border);border-radius:8px;font-size:13px;width:120px;">
          </div>
          <div>
            <div class="sc-label" style="margin-bottom:6px;">Tỷ trọng tối đa mỗi mã (%)</div>
            <input type="number" id="pfMaxW" value="100" step="5" min="10" max="100" style="padding:8px 12px;background:var(--bg);border:1px solid var(--border);border-radius:8px;font-size:13px;width:120px;">
          </div>
        </div>
        <div style="display:flex;gap:12px;align-items:end;">
          <button onclick="resetPortfolio()" class="sc-btn">↺ Xóa hết</button>
          <button onclick="runPortfolioOptimize()" class="btn-ai" style="padding:12px 24px;">🎯 Tối Ưu</button>
        </div>
      </div>
      <div style="margin-top:12px;font-size:11px;color:var(--text-muted);text-align:right;">
        * SLSQP tối ưu + Monte Carlo 5000 danh mục · Mất ~10-20s
      </div>
    </div>

    <div id="pfResult" style="min-height:200px;">
      <div class="empty">
        <div class="empty-icon">💼</div>
        <div>Thêm 2-12 mã và bấm Tối Ưu</div>
      </div>
    </div>
  </div>
</div>

<div id="tab-deep-analyze" class="hidden">
  <div class="wrap">
    <h2 class="section-title">🔬 Phân Tích Chuyên Sâu (Định giá + Dupont + ROE ngành)</h2>
    <div class="table-card" style="padding:24px;">
      <div style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;">
        <input type="text" id="deepSymbol" class="chat-input" placeholder="VD: FPT"
               style="font-size:16px;font-weight:700;text-transform:uppercase;width:140px;text-align:center;">
        <input type="text" id="deepQuestion" class="chat-input"
               placeholder="Câu hỏi tùy chọn..."
               style="flex:1;min-width:250px;">
        <button onclick="runDeepAnalysis()" class="btn-ai">🔬 Phân Tích Sâu</button>
      </div>
      <div id="deepResult" style="min-height:200px;">
        <div class="empty">
          <div class="empty-icon">🔬</div>
          <div>Nhập mã để phân tích định giá + ROE chuyên sâu</div>
        </div>
      </div>
    </div>
  </div>
</div>
<div id="tab-chat-ai" class="hidden">
  <div class="wrap">
    <h2 class="section-title">💬 Chat AI - Phân Tích Theo Mã</h2>
    <div class="table-card" style="padding:24px;">
      <div style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;">
        <input type="text" id="chatSymbol" class="chat-input" placeholder="VD: FPT" style="font-size:16px;font-weight:700;text-transform:uppercase;width:140px;text-align:center;">
        <input type="text" id="chatQuestion" class="chat-input" placeholder="Câu hỏi..." style="flex:1;min-width:250px;">
        <button onclick="askAI()" class="btn-ai">🚀 Phân Tích</button>
      </div>
      <div id="chatQuickSymbols" style="margin-bottom:20px;display:flex;gap:6px;flex-wrap:wrap;"></div>
      <div id="chatResult" style="min-height:200px;">
        <div class="empty"><div class="empty-icon">💬</div><div>Nhập mã cổ phiếu và câu hỏi để bắt đầu</div></div>
      </div>
    </div>
  </div>
</div>

<div class="modal-ov" id="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal" id="modalBody"></div>
</div>

<div class="toast" id="toast"></div>

<footer>
  🕒 Cập nhật: <span id="lastUpdate">--</span> · 📊 Tổng: <span id="fTotal">0</span> mã
</footer>

<script>
const STOCK_DATA = __DATA__;
const VALUATION_DATA = __VALUATION__;
const SCORING_DATA = __SCORING__;
const INDUSTRY_DATA = __INDUSTRY__;
const INDUSTRY_ROE_DATA = __INDUSTRY_ROE__;
const TECHNICAL_DATA = __TECHNICAL__;
const RSS_NEWS = __RSS_NEWS__;
const GROUP_DATA = __GROUPS__;
const UPDATE_TIME = "__TIME__";
let currentTab='stocks', currentPage=1;

function switchTab(tab,btn){
  currentTab=tab;
  document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');

  var allTabs = ['stocks','analysis','valuation','technical','industry','industry-compare','ai-report','news','ssi-report','chat-ai','deep-analyze','watchlist','compare','portfolio'];
  allTabs.forEach(function(t){
    var el = document.getElementById('tab-'+t);
    if (el) el.classList.add('hidden');
  });

  var showGroup = function(tabs){
    tabs.forEach(function(t){
      var el = document.getElementById('tab-'+t);
      if (el) el.classList.remove('hidden');
    });
  };

  if (tab === 'stocks') showGroup(['stocks']);
  else if (tab === 'analysis') showGroup(['analysis','valuation','technical','industry','industry-compare']);
  else if (tab === 'ai-report') showGroup(['ai-report']);
  else if (tab === 'ssi-report') showGroup(['ssi-report']);
  else if (tab === 'news') showGroup(['news']);
  else if (tab === 'deep-analyze') showGroup(['deep-analyze']);
  else if (tab === 'watchlist') showGroup(['watchlist']);
  else if (tab === 'compare') showGroup(['compare']);
  else if (tab === 'portfolio') showGroup(['portfolio']);

  if (tab === 'analysis') {
    renderAnalysis();
    renderValuation();
    renderTechnical();
    renderIndustry();
    renderIndustryCompare();
  }
  if (tab === 'ai-report') renderAIReport();
  if (tab === 'ssi-report') renderSSIReports();
  if (tab === 'news') renderNews();
  if (tab === 'deep-analyze') initDeepAnalyze();
  if (tab === 'watchlist') renderWatchlist();
  if (tab === 'compare') initCompare();
  initPortfolio();
  if (tab === 'portfolio') initPortfolio();
}

function getFiltered(){
  const q=document.getElementById('search').value.toUpperCase().trim();
  const group=document.getElementById('groupFilter').value;
  let d=_filteredByScreener().filter(s=>{
    if(group){
      const groupSymbols=GROUP_DATA[group]||[];
      if(!groupSymbols.includes(s.symbol))return false;
    }
    if(q&&!s.symbol.includes(q))return false;
    return true;
  });
  const sb=document.getElementById('sortBy').value;
  d.sort((a,b)=>{
    if(sb==='symbol')return a.symbol.localeCompare(b.symbol);
    if(sb==='pct_desc')return (b.pct||0)-(a.pct||0);
    if(sb==='pct_asc')return (a.pct||0)-(b.pct||0);
    if(sb==='vol_desc')return (b.volume||0)-(a.volume||0);
    return 0;
  });
  return d;
}

function renderTable(){
  const data=getFiltered();
  const pp=parseInt(document.getElementById('perPage').value);
  const tp=Math.ceil(data.length/pp)||1;
  if(currentPage>tp)currentPage=tp;
  const pd=data.slice((currentPage-1)*pp, currentPage*pp);
  const tb=document.getElementById('tbody');
  if(pd.length===0){
    tb.innerHTML='<tr><td colspan="10" class="empty">Không có dữ liệu</td></tr>';
  } else {
    tb.innerHTML=pd.map(s=>{
      const c=s.pct>0?'up':(s.pct<0?'down':'ref');
      const rc=s.pct>0?'row-up':(s.pct<0?'row-down':'');
      const sg=s.pct>0?'+':'';
      const fn=s.foreign_net||0;
      return '<tr class="'+rc+'" onclick="openModal(\''+s.symbol+'\')">'+
        '<td><span class="sym">'+s.symbol+'</span><span class="exch">'+(s.exchange||'')+'</span></td>'+
        '<td class="num" style="color:#8B5CF6;font-weight:700;">'+(s.ceiling?fmtVND(s.ceiling):'—')+'</td>'+
        '<td class="num" style="color:#06B6D4;font-weight:700;">'+(s.floor?fmtVND(s.floor):'—')+'</td>'+
        '<td class="num" style="color:#F59E0B;font-weight:700;">'+(s.reference?fmtVND(s.reference):'—')+'</td>'+
        '<td class="num" style="font-weight:700;">'+fmtVND(s.close)+'</td>'+
        '<td class="num '+c+'">'+(s.change>0?'+':'')+fmtVND(s.change)+'</td>'+
        '<td class="num '+c+'">'+sg+(s.pct||0).toFixed(2)+'%</td>'+
        '<td class="num">'+fmtVol(s.volume)+'</td>'+
        '<td class="num '+(fn>0?'up':(fn<0?'down':''))+'">'+(fn>0?'+':'')+fmtVol(fn)+'</td>'+
        '<td style="text-align:center;">'+renderScoreBadge(s.symbol)+'</td>'+
        '<td style="font-size:11px;color:var(--text-muted);font-family:var(--font-mono);">'+(s.time||'—')+'</td>'+
      '</tr>';
    }).join('');
  }
  renderPg(tp,data.length);
}

function renderPg(tp,total){
  const el=document.getElementById('pagination');
  if(tp<=1){el.innerHTML='<span class="pg-info">Tổng '+total+' mã</span>';return;}
  let h='<button class="pg-btn" '+(currentPage===1?'disabled':'')+' onclick="goPage('+(currentPage-1)+')">«</button>';
  const s=Math.max(1,currentPage-3), e=Math.min(tp,currentPage+3);
  for(let i=s;i<=e;i++)h+='<button class="pg-btn '+(i===currentPage?'active':'')+'" onclick="goPage('+i+')">'+i+'</button>';
  if(e<tp)h+='<button class="pg-btn" onclick="goPage('+tp+')">'+tp+'</button>';
  h+='<button class="pg-btn" '+(currentPage===tp?'disabled':'')+' onclick="goPage('+(currentPage+1)+')">»</button>';
  h+='<span class="pg-info">Tổng '+total+' mã</span>';
  el.innerHTML=h;
}
function goPage(p){currentPage=p;renderTable();window.scrollTo({top:250,behavior:'smooth'})}

function getRsiClass(r){
  if(r==null)return '';
  if(r<30)return 'rsi-oversold';
  if(r>70)return 'rsi-overbought';
  return 'rsi-neutral';
}

function closeModal(){document.getElementById('modal').classList.remove('active')}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal()});

function openModal(sym){
  const s=STOCK_DATA.find(x=>x.symbol===sym);
  if(!s)return;
  const c=s.pct>0?'sv-g':(s.pct<0?'sv-r':'sv-y');
  const v=VALUATION_DATA[sym]||{};
  const ind=INDUSTRY_DATA[sym]||{};
  const ta=TECHNICAL_DATA[sym]||{};
  const fn=s.foreign_net||0;
  let bidAskHtml='';
  if(s.bid_price_1 || s.ask_price_1){
    bidAskHtml='<div style="margin-top:20px;">'+
      '<div style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-bottom:10px;">📊 Bảng Khớp Lệnh</div>'+
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">'+
        '<div style="background:var(--green-bg);padding:12px;border-radius:10px;border:1px solid var(--green-border);">'+
          '<div style="font-weight:700;color:var(--green);margin-bottom:8px;font-size:13px;">🟢 Bên Mua</div>'+
          '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;font-size:11px;">'+
            '<div style="color:var(--text-muted);">Giá</div><div style="color:var(--text-muted);">KL</div><div style="color:var(--text-muted);">Lệnh</div>'+
            '<div style="font-weight:700;color:var(--green);">'+(s.bid_price_1?fmtVND(s.bid_price_1):'—')+'</div>'+
            '<div style="font-family:var(--font-mono);">'+(s.bid_vol_1?fmtVol(s.bid_vol_1):'—')+'</div><div>1</div>'+
            '<div style="font-weight:700;color:var(--green);">'+(s.bid_price_2?fmtVND(s.bid_price_2):'—')+'</div>'+
            '<div style="font-family:var(--font-mono);">'+(s.bid_vol_2?fmtVol(s.bid_vol_2):'—')+'</div><div>2</div>'+
            '<div style="font-weight:700;color:var(--green);">'+(s.bid_price_3?fmtVND(s.bid_price_3):'—')+'</div>'+
            '<div style="font-family:var(--font-mono);">'+(s.bid_vol_3?fmtVol(s.bid_vol_3):'—')+'</div><div>3</div>'+
          '</div>'+
        '</div>'+
        '<div style="background:var(--red-bg);padding:12px;border-radius:10px;border:1px solid var(--red-border);">'+
          '<div style="font-weight:700;color:var(--red);margin-bottom:8px;font-size:13px;">🔴 Bên Bán</div>'+
          '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;font-size:11px;">'+
            '<div style="color:var(--text-muted);">Giá</div><div style="color:var(--text-muted);">KL</div><div style="color:var(--text-muted);">Lệnh</div>'+
            '<div style="font-weight:700;color:var(--red);">'+(s.ask_price_1?fmtVND(s.ask_price_1):'—')+'</div>'+
            '<div style="font-family:var(--font-mono);">'+(s.ask_vol_1?fmtVol(s.ask_vol_1):'—')+'</div><div>1</div>'+
            '<div style="font-weight:700;color:var(--red);">'+(s.ask_price_2?fmtVND(s.ask_price_2):'—')+'</div>'+
            '<div style="font-family:var(--font-mono);">'+(s.ask_vol_2?fmtVol(s.ask_vol_2):'—')+'</div><div>2</div>'+
            '<div style="font-weight:700;color:var(--red);">'+(s.ask_price_3?fmtVND(s.ask_price_3):'—')+'</div>'+
            '<div style="font-family:var(--font-mono);">'+(s.ask_vol_3?fmtVol(s.ask_vol_3):'—')+'</div><div>3</div>'+
          '</div>'+
        '</div>'+
      '</div>'+
    '</div>';
  }
  var tradePlanHtml = '';
  var tp = ta.trade_plan;
  if (tp && tp.entry_low) {
    var confidenceColor = {'Cao':'var(--green)','Trung bình':'var(--amber)','Thấp':'var(--red)'}[tp.confidence] || 'var(--text-muted)';
    var adviceColor = tp.advice.indexOf('MUA')>=0 ? 'var(--green)' : (tp.advice.indexOf('KHÔNG')>=0||tp.advice.indexOf('HẠN CHẾ')>=0 ? 'var(--red)' : 'var(--amber)');
    tradePlanHtml = '<div style="margin-top:20px;background:var(--primary-bg);padding:16px;border-radius:12px;border:1px solid var(--primary-bg-hover);">'
      + '<div style="font-weight:700;color:var(--primary);margin-bottom:12px;font-size:14px;">📋 Kế Hoạch Giao Dịch Tham Khảo</div>'
      + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">'
      + '<div class="m-item"><div class="m-lb">Vùng vào lệnh</div><div class="m-vl">'+fmtVND(tp.entry_low)+' - '+fmtVND(tp.entry_high)+'</div></div>'
      + '<div class="m-item"><div class="m-lb">Mục tiêu</div><div class="m-vl sv-g">'+fmtVND(tp.target)+' ('+(tp.upside_pct>0?'+':'')+tp.upside_pct+'%)</div></div>'
      + '<div class="m-item"><div class="m-lb">Cắt lỗ</div><div class="m-vl sv-r">'+fmtVND(tp.stop)+' ('+tp.downside_pct+'%)</div></div>'
      + '<div class="m-item"><div class="m-lb">R:R</div><div class="m-vl">'+(tp.rr_ratio||'—')+'</div></div>'
      + '<div class="m-item"><div class="m-lb">Độ tin cậy</div><div class="m-vl" style="color:'+confidenceColor+';">'+tp.confidence+'</div></div>'
      + '</div>'
      + '<div style="margin-top:12px;padding:10px;background:'+adviceColor+';color:white;border-radius:8px;font-weight:700;text-align:center;font-size:13px;">'+tp.advice+'</div>'
      + '</div>';
  }
  var ctckHtml = '<div id="modalCtck" style="margin-top:20px;"></div>';
  var riskHtml = '<div id="modalRisk" style="margin-top:20px;"></div>';
  var chartHtml = '<div style="margin-top:20px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px;">'
    + '<div style="font-weight:700;color:var(--primary);margin-bottom:10px;font-size:14px;">📈 Biểu Đồ Kỹ Thuật (90 phiên)</div>'
    + '<div id="modalChart" style="text-align:center;min-height:200px;">'
    + '<div style="padding:40px;color:var(--text-muted);font-size:12px;">⏳ Đang tải biểu đồ...</div>'
    + '</div></div>';
  document.getElementById('modalBody').innerHTML=
    '<button class="modal-x" onclick="closeModal()">✕</button>'+
    '<h2>'+s.symbol+'</h2>'+
    '<div class="modal-sub">🏢 '+(s.exchange||'—')+' · 🏷️ '+(ind.group||'N/A')+' · 🕒 '+(s.time||'—')+'</div>'+
    '<div class="m-grid">'+
      '<div class="m-item" style="background:#F5F3FF;border-color:#DDD6FE;">'+
        '<div class="m-lb" style="color:#7C3AED;">Trần (Ceiling)</div>'+
        '<div class="m-vl" style="color:#8B5CF6;">'+(s.ceiling?fmtVND(s.ceiling):'—')+'</div>'+
      '</div>'+
      '<div class="m-item" style="background:#ECFEFF;border-color:#A5F3FC;">'+
        '<div class="m-lb" style="color:#0891B2;">Sàn (Floor)</div>'+
        '<div class="m-vl" style="color:#06B6D4;">'+(s.floor?fmtVND(s.floor):'—')+'</div>'+
      '</div>'+
      '<div class="m-item" style="background:#FFFBEB;border-color:#FDE68A;">'+
        '<div class="m-lb" style="color:#B45309;">TC (Reference)</div>'+
        '<div class="m-vl" style="color:#F59E0B;">'+(s.reference?fmtVND(s.reference):'—')+'</div>'+
      '</div>'+
      '<div class="m-item"><div class="m-lb">Giá khớp</div><div class="m-vl">'+fmtVND(s.close)+'</div></div>'+
      '<div class="m-item"><div class="m-lb">% Thay đổi</div><div class="m-vl '+c+'">'+((s.pct>0?'+':'')+(s.pct||0).toFixed(2))+'%</div></div>'+
      '<div class="m-item"><div class="m-lb">Khối lượng</div><div class="m-vl">'+fmtVol(s.volume)+'</div></div>'+
      '<div class="m-item"><div class="m-lb">Mở cửa</div><div class="m-vl">'+(s.open?fmtVND(s.open):'—')+'</div></div>'+
      '<div class="m-item"><div class="m-lb">Cao nhất</div><div class="m-vl">'+(s.high?fmtVND(s.high):'—')+'</div></div>'+
      '<div class="m-item"><div class="m-lb">Thấp nhất</div><div class="m-vl">'+(s.low?fmtVND(s.low):'—')+'</div></div>'+
      '<div class="m-item"><div class="m-lb">KL Ngoại ròng</div><div class="m-vl '+(fn>0?'sv-g':(fn<0?'sv-r':''))+'">'+((fn>0?'+':'')+fmtVol(fn))+'</div></div>'+
      '<div class="m-item"><div class="m-lb">P/E</div><div class="m-vl">'+(v.pe?v.pe+'x':'—')+'</div></div>'+
      '<div class="m-item"><div class="m-lb">ROE</div><div class="m-vl sv-g">'+(v.roe?v.roe+'%':'—')+'</div></div>'+
      '<div class="m-item"><div class="m-lb">MA20</div><div class="m-vl">'+(ta.ma20?fmtVND(ta.ma20):'—')+'</div></div>'+
      '<div class="m-item"><div class="m-lb">RSI14</div><div class="m-vl '+getRsiClass(ta.rsi14)+'">'+(ta.rsi14||'—')+'</div></div>'+
    '</div>'+bidAskHtml+tradePlanHtml+chartHtml+ctckHtml+riskHtml;
  document.getElementById('modal').classList.add('active');
  setTimeout(function(){ loadModalChart(sym); }, 50);
}

function renderAnalysis(){
  const topUp=[...STOCK_DATA].filter(s=>s.pct>0).sort((a,b)=>b.pct-a.pct).slice(0,20);
  const topDown=[...STOCK_DATA].filter(s=>s.pct<0).sort((a,b)=>a.pct-b.pct).slice(0,20);
  const topVol=[...STOCK_DATA].sort((a,b)=>(b.volume||0)-(a.volume||0)).slice(0,20);
  const topForeign=[...STOCK_DATA].filter(s=>s.foreign_net>0).sort((a,b)=>b.foreign_net-a.foreign_net).slice(0,20);
  const sections=[
    {title:'📈 Top 20 tăng mạnh',data:topUp,color:'green',metric:s=>'+'+s.pct.toFixed(2)+'%'},
    {title:'📉 Top 20 giảm mạnh',data:topDown,color:'red',metric:s=>s.pct.toFixed(2)+'%'},
    {title:'💧 Top 20 thanh khoản',data:topVol,color:'primary',metric:s=>fmtVol(s.volume)},
    {title:'🌍 Top 20 ngoại mua ròng',data:topForeign,color:'green',metric:s=>'+'+fmtVol(s.foreign_net)}
  ];
  document.getElementById('analysisList').innerHTML=sections.map(sec=>
    '<div class="tcard"><h3 style="color:var(--'+sec.color+');margin-bottom:14px;font-size:14px;font-weight:700;">'+sec.title+'</h3>'+
      '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px;">'+
        sec.data.map(s=>'<div onclick="openModal(\''+s.symbol+'\')" style="background:var(--bg);padding:12px;border-radius:8px;cursor:pointer;border:1px solid var(--border);">'+
          '<div style="display:flex;justify-content:space-between;"><span style="font-weight:700;color:var(--primary);font-family:var(--font-mono);">'+s.symbol+'</span>'+
          '<span style="font-weight:700;color:var(--'+sec.color+');font-size:12px;font-family:var(--font-mono);">'+sec.metric(s)+'</span></div>'+
          '<div style="font-size:11px;color:var(--text-muted);margin-top:6px;">'+s.exchange+' · '+fmtVND(s.close)+' đ</div>'+
        '</div>').join('')+
      '</div></div>').join('');
}

function renderValuation(){
  const body=document.getElementById('valuationBody');
  const entries=Object.values(VALUATION_DATA);
  if(entries.length===0){body.innerHTML='<tr><td colspan="7" class="empty">Chưa có dữ liệu</td></tr>';return;}
  body.innerHTML=entries.map(v=>
    '<tr onclick="openModal(\''+v.symbol+'\')">'+
      '<td><span class="sym">'+v.symbol+'</span></td>'+
      '<td class="num">'+(v.pe?v.pe+'x':'—')+'</td>'+
      '<td class="num">'+(v.pb?v.pb+'x':'—')+'</td>'+
      '<td class="num '+(v.roe>15?'up':(v.roe<5?'down':''))+'">'+(v.roe?v.roe+'%':'—')+'</td>'+
      '<td class="num">'+(v.roa?v.roa+'%':'—')+'</td>'+
      '<td class="num">'+(v.eps?fmtVND(v.eps):'—')+'</td>'+
      '<td class="num">'+(v.bvps?fmtVND(v.bvps):'—')+'</td>'+
    '</tr>').join('');
}

function renderTechnical(){
  const body=document.getElementById('technicalBody');
  const entries=Object.values(TECHNICAL_DATA);
  if(entries.length===0){body.innerHTML='<tr><td colspan="6" class="empty">Chưa có dữ liệu</td></tr>';return;}
  body.innerHTML=entries.map(t=>{
    const stock=STOCK_DATA.find(x=>x.symbol===t.symbol)||{};
    const close=stock.close||0;
    const sigClass=t.signal==='Tăng'?'up':(t.signal==='Giảm'?'down':'ref');
    return '<tr onclick="openModal(\''+t.symbol+'\')">'+
      '<td><span class="sym">'+t.symbol+'</span></td>'+
      '<td class="num">'+(close?fmtVND(close):'—')+'</td>'+
      '<td class="num">'+(t.ma20?fmtVND(t.ma20):'—')+'</td>'+
      '<td class="num">'+(t.ma50?fmtVND(t.ma50):'—')+'</td>'+
      '<td class="num '+getRsiClass(t.rsi14)+'">'+(t.rsi14||'—')+'</td>'+
      '<td style="text-align:center;"><span class="'+sigClass+'" style="font-weight:700;">'+(t.signal||'—')+'</span></td>'+
    '</tr>';
  }).join('');
}

function renderIndustry(){
  const groups={};
  Object.values(INDUSTRY_DATA).forEach(info=>{
    const g=info.group||'Khác';
    (groups[g]=groups[g]||[]).push(info.symbol);
  });
  const sorted=Object.entries(groups).sort((a,b)=>b[1].length-a[1].length);
  document.getElementById('industryStats').innerHTML=sorted.map(([g,syms])=>
    '<div class="stat"><div class="stat-lb">'+g+'</div><div class="stat-vl sv-b">'+syms.length+'</div></div>'
  ).join('');
  document.getElementById('industryList').innerHTML=sorted.map(([g,syms])=>
    '<div class="tcard"><h3 style="color:var(--primary);margin-bottom:14px;font-size:14px;font-weight:700;">🏢 '+g+' ('+syms.length+' mã)</h3>'+
      '<div style="display:flex;flex-wrap:wrap;gap:8px;">'+
        syms.map(s=>'<span onclick="openModal(\''+s+'\')" style="background:var(--primary-bg);padding:5px 12px;border-radius:6px;font-size:12px;font-weight:700;color:var(--primary);cursor:pointer;font-family:var(--font-mono);">'+s+'</span>').join('')+
      '</div></div>').join('');
}

function renderIndustryCompare(){
  const el=document.getElementById('industryCompareList');
  const sorted=Object.entries(INDUSTRY_ROE_DATA).sort((a,b)=>b[1].avg_roe-a[1].avg_roe);
  if(sorted.length===0){el.innerHTML='<div class="empty"><div class="empty-icon">📊</div><div>Chưa có dữ liệu ROE</div></div>';return;}
  const maxRoe=sorted[0][1].avg_roe;
  el.innerHTML=sorted.map(([ind,info])=>{
    const pct=(info.avg_roe/maxRoe)*100;
    return '<div class="tcard">'+
      '<div style="display:flex;justify-content:space-between;align-items:center;">'+
        '<span style="font-weight:700;color:var(--primary);font-size:14px;">🏢 '+ind+'</span>'+
        '<span style="font-weight:700;color:var(--green);font-size:18px;font-family:var(--font-mono);">'+info.avg_roe+'%</span>'+
      '</div>'+
      '<div class="roe-bar"><div class="roe-fill" style="width:'+pct+'%;"></div></div>'+
      '<div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text-secondary);">'+
        '<span>'+info.count+' mã</span>'+
        '<span>Cao: <b style="color:var(--green)">'+info.max_roe+'%</b> · Thấp: <b style="color:var(--red)">'+info.min_roe+'%</b></span>'+
      '</div></div>';
  }).join('');
}

function renderAIReport(){ loadPdfList(); }

var _pdfAllData = [];

function _parsePdfDate(filename){
  // Format 1: BaoCao_ATO_11102026.pdf -> 2026-10-11
  // Format 2: NhanDinhThiTruong_11102026_2328.pdf -> 2026-10-11
  var m = filename.match(/(\d{2})(\d{2})(\d{4})/);
  if (!m) return null;
  return m[3] + '-' + m[2] + '-' + m[1];  // YYYY-MM-DD
}

function _formatDateVN(isoDate){
  if (!isoDate) return '';
  var p = isoDate.split('-');
  if (p.length !== 3) return isoDate;
  return p[2] + '/' + p[1] + '/' + p[0];
}

function _dateLabel(isoDate){
  if (!isoDate) return 'Không xác định';
  var d = new Date(isoDate);
  var days = ['CN','T2','T3','T4','T5','T6','T7'];
  var dow = days[d.getDay()];
  var today = new Date();
  var todayIso = today.getFullYear() + '-' + 
    String(today.getMonth()+1).padStart(2,'0') + '-' + 
    String(today.getDate()).padStart(2,'0');
  var yesterday = new Date(today);
  yesterday.setDate(today.getDate()-1);
  var yIso = yesterday.getFullYear() + '-' + 
    String(yesterday.getMonth()+1).padStart(2,'0') + '-' + 
    String(yesterday.getDate()).padStart(2,'0');
  var label = _formatDateVN(isoDate) + ' (' + dow + ')';
  if (isoDate === todayIso) label = '🔴 Hôm nay · ' + label;
  else if (isoDate === yIso) label = '🟡 Hôm qua · ' + label;
  return label;
}

async function loadPdfList(){
  var el = document.getElementById('pdfList');
  var countEl = document.getElementById('pdfCount');
  var filterEl = document.getElementById('pdfDateFilter');
  if (!el) return;
  el.innerHTML = '<div class="empty"><div class="empty-icon">⏳</div><div>Đang tải...</div></div>';
  try {
    var res = await fetch('http://localhost:5000/api/pdfs');
    var data = await res.json();
    if (data.error){
      el.innerHTML = '<div class="empty"><div class="empty-icon">❌</div><div>' + data.error + '</div></div>';
      return;
    }
    var pdfs = data.pdfs || [];
    _pdfAllData = pdfs;
    if (countEl) countEl.textContent = 'Tổng: ' + pdfs.length + ' file';

    if (pdfs.length === 0){
      el.innerHTML = '<div class="empty"><div class="empty-icon">📄</div><div>Chưa có file PDF</div></div>';
      return;
    }

    // Group by date
    var dateMap = {};
    pdfs.forEach(function(p){
      var d = _parsePdfDate(p.filename);
      if (!d) d = 'unknown';
      if (!dateMap[d]) dateMap[d] = 0;
      dateMap[d]++;
    });

    // Sap xep ngay moi -> cu, 'unknown' xuong cuoi
    var dateKeys = Object.keys(dateMap).filter(function(k){ return k !== 'unknown'; }).sort().reverse();
    if (dateMap['unknown']) dateKeys.push('unknown');

    // Rebuild dropdown, giu lua chon cu neu co
    if (filterEl){
      var current = filterEl.value;
      filterEl.innerHTML = '<option value="">📅 Tất cả ngày (' + pdfs.length + ' file)</option>';
      dateKeys.forEach(function(d){
        var opt = document.createElement('option');
        opt.value = d;
        opt.textContent = d === 'unknown' 
          ? '📄 Không xác định (' + dateMap[d] + ')'
          : _dateLabel(d) + ' · ' + dateMap[d] + ' file';
        filterEl.appendChild(opt);
      });
      // Mac dinh chon ngay moi nhat neu lan dau
      if (!current && dateKeys.length > 0 && dateKeys[0] !== 'unknown'){
        filterEl.value = dateKeys[0];
      } else if (current){
        filterEl.value = current;
      }
    }

    renderPdfByDate();
  } catch(err){
    el.innerHTML = '<div class="empty"><div class="empty-icon">⚠️</div><div>Không kết nối được server</div></div>';
  }
}

function renderPdfByDate(){
  var el = document.getElementById('pdfList');
  var filterEl = document.getElementById('pdfDateFilter');
  if (!el) return;
  var selected = filterEl ? filterEl.value : '';
  var pdfs = _pdfAllData;

  // Filter theo ngay
  var filtered;
  if (selected === '') {
    filtered = pdfs.slice();
  } else if (selected === 'unknown') {
    filtered = pdfs.filter(function(p){ return !_parsePdfDate(p.filename); });
  } else {
    filtered = pdfs.filter(function(p){ return _parsePdfDate(p.filename) === selected; });
  }

  if (filtered.length === 0){
    el.innerHTML = '<div class="empty"><div class="empty-icon">📄</div><div>Không có báo cáo cho ngày này</div></div>';
    return;
  }

  // Neu dang xem "Tat ca ngay" -> nhom theo ngay de de xem
  if (selected === ''){
    var groups = {};
    filtered.forEach(function(p){
      var d = _parsePdfDate(p.filename) || 'unknown';
      if (!groups[d]) groups[d] = [];
      groups[d].push(p);
    });
    var keys = Object.keys(groups).filter(function(k){ return k !== 'unknown'; }).sort().reverse();
    if (groups['unknown']) keys.push('unknown');

    var html = '';
    keys.forEach(function(d){
      var items = groups[d];
      var label = d === 'unknown' ? '📄 Không xác định' : '📅 ' + _dateLabel(d);
      html += '<h3 style="color:var(--primary);margin:24px 0 12px;font-size:14px;font-weight:700;border-bottom:2px solid var(--border);padding-bottom:6px;">'
            + label + ' <span style="color:var(--text-muted);font-weight:500;font-size:12px;">(' + items.length + ' file)</span></h3>';
      // Nhan dinh thi truong truoc, roi session
      var market = items.filter(function(p){ return p.filename.indexOf('NhanDinh') === 0; });
      var sessions = items.filter(function(p){ return p.filename.indexOf('BaoCao_') === 0; });
      market.forEach(function(p){ html += renderPdfCard(p, 'purple'); });
      sessions.forEach(function(p){ html += renderPdfCard(p, 'primary'); });
      // Con lai
      items.filter(function(p){
        return p.filename.indexOf('NhanDinh') !== 0 && p.filename.indexOf('BaoCao_') !== 0;
      }).forEach(function(p){ html += renderPdfCard(p, 'primary'); });
    });
    el.innerHTML = html;
  } else {
    // Chi 1 ngay cu the
    var items = filtered;
    var market = items.filter(function(p){ return p.filename.indexOf('NhanDinh') === 0; });
    var sessions = items.filter(function(p){ return p.filename.indexOf('BaoCao_') === 0; });
    var others = items.filter(function(p){
      return p.filename.indexOf('NhanDinh') !== 0 && p.filename.indexOf('BaoCao_') !== 0;
    });
    var html = '';
    if (market.length > 0){
      html += '<h3 style="color:var(--purple);margin:16px 0 14px;font-size:14px;font-weight:700;">📰 Nhận Định Thị Trường (' + market.length + ')</h3>';
      html += market.map(function(p){ return renderPdfCard(p, 'purple'); }).join('');
    }
    if (sessions.length > 0){
      html += '<h3 style="color:var(--primary);margin:20px 0 14px;font-size:14px;font-weight:700;">📊 Báo Cáo Theo Phiên (' + sessions.length + ')</h3>';
      html += sessions.map(function(p){ return renderPdfCard(p, 'primary'); }).join('');
    }
    if (others.length > 0){
      html += '<h3 style="color:var(--primary);margin:20px 0 14px;font-size:14px;font-weight:700;">📄 Khác (' + others.length + ')</h3>';
      html += others.map(function(p){ return renderPdfCard(p, 'primary'); }).join('');
    }
    el.innerHTML = html;
  }
}

function renderPdfCard(p, color){
  var sessionLabel = '';
  var sessionTime = '';
  if (p.filename.indexOf('_ATO_') >= 0){ sessionLabel = 'PHIÊN MỞ CỬA (ATO)'; sessionTime = '09:00 - 09:15'; }
  else if (p.filename.indexOf('_SANG_') >= 0){ sessionLabel = 'PHIÊN SÁNG'; sessionTime = '09:15 - 11:30'; }
  else if (p.filename.indexOf('_CHIEU_') >= 0){ sessionLabel = 'PHIÊN CHIỀU'; sessionTime = '13:00 - 14:30'; }
  else if (p.filename.indexOf('_ATC_') >= 0){ sessionLabel = 'PHIÊN ĐÓNG CỬA (ATC)'; sessionTime = '14:30 - 14:45'; }
  else if (p.filename.indexOf('NhanDinh') === 0){ sessionLabel = 'NHẬN ĐỊNH THỊ TRƯỜNG'; sessionTime = 'Báo cáo AI'; }
  else { sessionLabel = 'BÁO CÁO'; }
  
  var dateStr = 'Không xác định';
  var dayOfWeek = '';
  var iso = _parsePdfDate(p.filename);
  if (iso){
    dateStr = _formatDateVN(iso);
    var d = new Date(iso);
    var days = ['Chủ Nhật','Thứ Hai','Thứ Ba','Thứ Tư','Thứ Năm','Thứ Sáu','Thứ Bảy'];
    dayOfWeek = days[d.getDay()];
  }
  
  var colorVar = 'var(--' + color + ')';
  return '<div class="tcard" style="border-left:4px solid ' + colorVar + ';">'
    + '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;">'
    + '<div style="flex:1;min-width:280px;">'
    + '<div style="font-weight:700;font-size:15px;color:' + colorVar + ';margin-bottom:10px;">' + sessionLabel + '</div>'
    + '<div style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:8px;">'
    + '<div style="display:flex;align-items:center;gap:6px;"><span>📅</span>'
    + '<span style="font-weight:600;font-size:13px;font-family:var(--font-mono);">Ngày ' + dateStr + '</span>'
    + (dayOfWeek ? '<span style="color:var(--text-muted);font-size:12px;">(' + dayOfWeek + ')</span>' : '')
    + '</div>'
    + '<div style="display:flex;align-items:center;gap:6px;"><span>🕒</span>'
    + '<span style="font-size:12px;color:var(--text-secondary);font-family:var(--font-mono);">' + sessionTime + '</span>'
    + '</div></div>'
    + '<div style="font-size:11px;color:var(--text-muted);font-family:var(--font-mono);">📁 ' + p.filename + ' · ' + p.size_kb + ' KB</div>'
    + '</div>'
    + '<div style="display:flex;gap:8px;">'
    + '<a href="http://localhost:5000/pdfs/' + p.filename + '" target="_blank" rel="noopener noreferrer" class="report-link">👁️ Xem</a>'
    + '<a href="http://localhost:5000/pdfs/' + p.filename + '" download class="report-link green">📥 Tải</a>'
    + '</div></div></div>';
}

function renderScoreBadge(sym){
  var s = (typeof SCORING_DATA !== 'undefined') ? SCORING_DATA[sym] : null;
  if(!s) return '<span style="color:var(--text-muted);font-size:11px;">—</span>';
  var cls = {'positive':'score-pos','neutral':'score-neu','negative':'score-neg'}[s.label] || 'score-neu';
  var icon = {'positive':'✅','neutral':'⚪','negative':'❌'}[s.label] || '⚪';
  return '<span class="score-badge '+cls+'" title="'+(s.label_vn||'')+' (tổng: '+(s.total>0?'+':'')+s.total+')">'+icon+' '+(s.total>0?'+':'')+s.total+'</span>';
}

function renderRiskSection(r){
  if(!r || r.error) return '';
  var betaColor = 'sv-y';
  if(r.beta !== null && r.beta !== undefined){
    if(r.beta < 0.8) betaColor = 'sv-g';
    else if(r.beta > 1.3) betaColor = 'sv-r';
  }
  var sharpeColor = 'sv-y';
  if(r.sharpe !== null && r.sharpe !== undefined){
    if(r.sharpe > 0.5) sharpeColor = 'sv-g';
    else if(r.sharpe < 0) sharpeColor = 'sv-r';
  }
  var cagrColor = 'sv-y';
  if(r.cagr_2y !== null && r.cagr_2y !== undefined){
    if(r.cagr_2y > 0.05) cagrColor = 'sv-g';
    else if(r.cagr_2y < -0.05) cagrColor = 'sv-r';
  }
  var ddColor = 'sv-y';
  if(r.max_drawdown !== null && r.max_drawdown !== undefined){
    if(r.max_drawdown > -0.2) ddColor = 'sv-g';
    else if(r.max_drawdown < -0.4) ddColor = 'sv-r';
  }

  var fmtPct = function(v){ return (v === null || v === undefined) ? '—' : (v*100).toFixed(2) + '%'; };
  var fmtNum = function(v, d){ d = d || 2; return (v === null || v === undefined) ? '—' : Number(v).toFixed(d); };

  var html = '<h3 style="color:var(--primary);margin:24px 0 14px;font-size:15px;font-weight:700;">📊 Chỉ Số Rủi Ro (1-2 năm)</h3>';
  html += '<div class="tcard">';
  html += '<div class="m-grid">';
  html += '<div class="m-item"><div class="m-lb">Beta (so VNINDEX)</div><div class="m-vl '+betaColor+'">'+fmtNum(r.beta)+'</div></div>';
  html += '<div class="m-item"><div class="m-lb">Độ lệch chuẩn/năm (σ)</div><div class="m-vl">'+fmtPct(r.sigma_annual)+'</div></div>';
  html += '<div class="m-item"><div class="m-lb">CAGR 1 năm</div><div class="m-vl '+cagrColor+'">'+fmtPct(r.cagr_1y)+'</div></div>';
  html += '<div class="m-item"><div class="m-lb">CAGR 2 năm</div><div class="m-vl '+cagrColor+'">'+fmtPct(r.cagr_2y)+'</div></div>';
  html += '<div class="m-item"><div class="m-lb">Sharpe Ratio</div><div class="m-vl '+sharpeColor+'">'+fmtNum(r.sharpe)+'</div></div>';
  html += '<div class="m-item"><div class="m-lb">Max Drawdown</div><div class="m-vl '+ddColor+'">'+fmtPct(r.max_drawdown)+'</div></div>';
  html += '</div>';
  html += '<div style="margin-top:12px;font-size:11px;color:var(--text-muted);">* Rf = ' + ((r.rf_rate || 0.033)*100).toFixed(1) + '%/năm · Dữ liệu ' + (r.days || 0) + ' phiên · Cập nhật: ' + (r.updated || '') + '</div>';
  html += '</div>';
  return html;
}

function renderSentimentBadge(n){
  var label = n.sentiment_label || 'neutral';
  var score = n.sentiment_score || 0;
  var cfg = {
    'positive': {icon:'✅', color:'var(--green)', bg:'var(--green-bg)', text:'Tích cực'},
    'negative': {icon:'❌', color:'var(--red)', bg:'var(--red-bg)', text:'Tiêu cực'},
    'neutral':  {icon:'⚪', color:'var(--text-muted)', bg:'var(--bg-soft)', text:'Trung lập'}
  };
  var c = cfg[label] || cfg['neutral'];
  return '<span style="display:inline-block;background:'+c.bg+';color:'+c.color+';padding:3px 8px;border-radius:6px;font-size:10px;font-weight:700;margin-left:6px;">'+c.icon+' '+c.text+(score?' ('+score+')':'')+'</span>';
}

async function loadRiskFor(symbol){
  try {
    var res = await fetch('http://localhost:5000/api/risk/' + symbol);
    var data = await res.json();
    return data;
  } catch(err){ return null; }
}

async function loadModalChart(symbol){
  var el = document.getElementById('modalChart');
  if(!el) return;
  try {
    var res = await fetch('http://localhost:5000/api/chart/' + symbol);
    var data = await res.json();
    if(data.error){
      el.innerHTML = '<div style="padding:20px;color:var(--red);font-size:12px;">⚠️ Không tải được biểu đồ</div>';
    } else {
      el.innerHTML = '<img src="' + data.image + '" style="max-width:100%;border-radius:8px;display:block;">';
    }
  } catch(err){
    el.innerHTML = '<div style="padding:20px;color:var(--red);font-size:12px;">⚠️ Lỗi kết nối</div>';
  }
  // Load khuyen nghi CTCK
  try {
    var ctck = await loadCtckFor(symbol);
    var elC = document.getElementById('modalCtck');
    if(elC){
      if(ctck && ctck.found){
        elC.innerHTML = renderCtckSection(ctck, symbol);
      } else {
        elC.innerHTML = '';
      }
    }
  } catch(e) { console.warn('CTCK modal:', e); }
  // Load risk
  try {
    var risk = await loadRiskFor(symbol);
    var elR = document.getElementById('modalRisk');
    if(elR && risk && risk.found !== false){
      elR.innerHTML = renderRiskSection(risk);
    } else if(elR){
      elR.innerHTML = '';
    }
  } catch(e) { console.warn('Risk modal:', e); }
}

function renderNews(){
  const el=document.getElementById('newsList');
  const filter=document.getElementById('newsCategoryFilter').value;
  if(document.getElementById('newsCategoryFilter').options.length<=1 && RSS_NEWS.length>0){
    const cats=[...new Set(RSS_NEWS.map(n=>n.category))];
    cats.forEach(c=>{document.getElementById('newsCategoryFilter').innerHTML+='<option value="'+c+'">'+c+'</option>';});
  }
  if(!RSS_NEWS||RSS_NEWS.length===0){
    el.innerHTML='<div class="empty"><div class="empty-icon">📰</div><div>Chưa có tin tức</div></div>';return;
  }
  let filtered=RSS_NEWS.filter(n=>!filter||n.category===filter);
  el.innerHTML=filtered.map(n=>
    '<div class="news-item"><span class="news-cat">'+n.category+'</span>'+renderSentimentBadge(n)+
      '<div class="news-title"><a href="'+n.link+'" target="_blank">'+n.title+'</a></div>'+
      '<div class="news-desc">'+(n.description||'')+'</div>'+
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:10px;gap:12px;flex-wrap:wrap;">'+
        '<span class="news-date">🕒 '+(n.pub_date||'')+'</span>'+
        '<a href="'+n.link+'" target="_blank" class="report-link" style="font-size:11px;padding:5px 12px;">🔗 Đọc bài gốc</a>'+
      '</div></div>').join('');
}

async function renderSSIReports(){
  if(window._reportsLoading){ console.log('[Reports] Dang tai'); return; }
  window._reportsLoading = true;
  const el=document.getElementById('ssiReportList');
  el.innerHTML = '<div class="empty"><div class="empty-icon">⏳</div><div>Đang tải báo cáo...</div></div>';
  try {
    const res = await fetch('http://localhost:5000/api/reports?force=' + (window._forceReports ? '1' : '0'));
    window._forceReports = false;
    const data = await res.json();
    if(data.error || !data.reports || data.reports.length === 0){
      el.innerHTML = '<div class="empty"><div class="empty-icon">📑</div><div>Chưa có báo cáo</div></div>';
      return;
    }
    const reports = data.reports;
    const updated = data.updated || '';

    // Phan loai theo field 'type'
    var analysis = [];   // Bao cao phan tich co phieu
    var industry = [];   // Bao cao nganh / vi mo
    var news = [];       // Tin tuc

    reports.forEach(function(r){
      var t = r.type || '';
      if (t === 'analysis') analysis.push(r);
      else if (t === 'industry') industry.push(r);
      else news.push(r);
    });

    var html = '<div style="color:var(--text-muted);font-size:12px;margin-bottom:16px;font-family:var(--font-mono);">';
    html += '🕒 Cập nhật: ' + updated + ' · Tổng: ' + reports.length + ' báo cáo';
    html += ' · 📊 PT cổ phiếu: ' + analysis.length;
    html += ' · 📈 Ngành: ' + industry.length;
    html += ' · 📰 Tin tức: ' + news.length;
    html += '</div>';

    var renderSection = function(title, color, items){
      if (items.length === 0) return '';
      var h = '<h3 style="color:var(--' + color + ');margin:20px 0 12px;font-size:14px;font-weight:700;">'
            + title + ' (' + items.length + ')</h3>';
      items.forEach(function(r){
        var dateHtml = r.date ? '<span style="font-family:var(--font-mono);font-weight:600;">📅 ' + r.date + '</span>' : '';
        h += '<div class="tcard" style="border-left:4px solid var(--' + color + ');padding:14px;">'
          + '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;">'
          + '<div style="flex:1;min-width:250px;">'
          + '<div style="font-weight:600;font-size:13px;margin-bottom:8px;">' + r.title + '</div>'
          + '<div style="display:flex;gap:16px;font-size:11px;color:var(--text-muted);flex-wrap:wrap;">'
          + dateHtml
          + '<span class="badge badge-primary">' + (r.source || '') + '</span>'
          + '<span class="badge" style="background:var(--bg-soft);color:var(--text-secondary);">' + (r.category || '') + '</span>'
          + '</div></div>'
          + '<a href="' + r.url + '" target="_blank" rel="noopener noreferrer" class="report-link" style="font-size:11px;padding:6px 14px;">🔗 Mở</a>'
          + '</div></div>';
      });
      return h;
    };

    html += renderSection('📊 Báo cáo phân tích cổ phiếu', 'primary', analysis);
    html += renderSection('📈 Phân tích ngành & vĩ mô', 'purple', industry);
    html += renderSection('📰 Tin tức thị trường', 'amber', news);

    el.innerHTML = html;
  } catch(err){
    el.innerHTML = '<div class="empty"><div class="empty-icon">⚠️</div><div>Không kết nối được server</div></div>';
  } finally {
    window._reportsLoading = false;
  }
}

function initChatAI(){
  const quick = document.getElementById('chatQuickSymbols');
  if(!quick) return;
  const hot = ['FPT','VNM','VCB','HPG','MWG','TCB','VHM','GAS','MSN','PNJ'];
  quick.innerHTML = '<span style="color:var(--text-muted);font-size:12px;font-weight:600;">Mã phổ biến:</span>' +
    hot.map(s => '<button onclick="document.getElementById(\'chatSymbol\').value=\''+s+'\';askAI()" style="padding:6px 12px;background:var(--primary-bg);color:var(--primary);border:1px solid var(--primary-bg-hover);border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;font-family:var(--font-mono);">'+s+'</button>').join('');
}

async function askAI(){
  const symbol = document.getElementById('chatSymbol').value.trim().toUpperCase();
  const question = document.getElementById('chatQuestion').value.trim();
  const result = document.getElementById('chatResult');
  if(!symbol){alert('Vui lòng nhập mã cổ phiếu');return;}
  result.innerHTML = '<div style="text-align:center;padding:40px;"><div style="font-size:36px;margin-bottom:12px;">⏳</div><div style="color:var(--text-secondary);">AI đang phân tích '+symbol+'...</div></div>';
  try {
    const res = await fetch('http://localhost:5000/api/analyze', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({symbol, question})
    });
    const data = await res.json();
    if(data.error){
      result.innerHTML = '<div class="empty"><div class="empty-icon">❌</div><div>'+data.error+'</div></div>';return;
    }
    const s = data.stock || {};
    const v = data.valuation || {};
    const ind = data.industry || {};
    const pct = s.pct || 0;
    const c = pct > 0 ? 'sv-g' : (pct < 0 ? 'sv-r' : 'sv-y');
    result.innerHTML =
      '<div style="background:var(--primary-bg);padding:20px;border-radius:12px;margin-bottom:20px;border:1px solid var(--primary-bg-hover);">'+
        '<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;">'+
          '<div><span style="font-weight:700;color:var(--primary);font-size:24px;font-family:var(--font-mono);">'+symbol+'</span>'+
            '<span style="color:var(--text-secondary);font-size:13px;margin-left:12px;">'+(ind.group||'N/A')+'</span></div>'+
          '<div style="font-size:14px;font-family:var(--font-mono);">'+
            '<span style="color:var(--text-secondary);">Giá:</span> <b>'+(s.close?Number(s.close).toLocaleString('vi-VN'):'—')+'</b>'+
            '<span class="'+c+'" style="margin-left:14px;font-weight:700;">'+(pct > 0 ? '+' : '')+pct.toFixed(2)+'%</span>'+
          '</div></div>'+
        '<div style="display:flex;gap:24px;margin-top:14px;font-size:12px;flex-wrap:wrap;font-family:var(--font-mono);">'+
          '<span>P/E: <b>'+(v.pe?v.pe+'x':'—')+'</b></span>'+
          '<span>P/B: <b>'+(v.pb?v.pb+'x':'—')+'</b></span>'+
          '<span>ROE: <b style="color:var(--green);">'+(v.roe?v.roe+'%':'—')+'</b></span>'+
          '<span>EPS: <b>'+(v.eps?Number(v.eps).toLocaleString('vi-VN'):'—')+'</b></span>'+
        '</div>'+
      '</div>'+
      '<div class="ai-box">'+renderMarkdown(data.report)+'</div>';
  } catch(err){
    result.innerHTML = '<div class="empty"><div class="empty-icon">⚠️</div><div>Không kết nối được server</div></div>';
  }
}

function initDeepAnalyze(){
  const el = document.getElementById('deepSymbol');
  if(el && !el.value) el.value = 'FPT';
}

async function runDeepAnalysis(){
  const symbol = (document.getElementById('deepSymbol').value || '').trim().toUpperCase();
  const question = (document.getElementById('deepQuestion').value || '').trim();
  const result = document.getElementById('deepResult');
  if(!symbol){alert('Vui lòng nhập mã cổ phiếu');return;}

  result.innerHTML = '<div style="text-align:center;padding:40px;">'+
    '<div style="font-size:36px;margin-bottom:12px;">⏳</div>'+
    '<div style="color:var(--text-secondary);">Đang phân tích chuyên sâu '+symbol+'...<br>'+
    '<span style="font-size:12px;color:var(--text-muted);">(lần đầu 3-4 phút nếu ngành chưa có cache, các lần sau tức thì)</span></div></div>';

  try {
    const res = await fetch('http://localhost:5000/api/deep-analyze', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({symbol, question})
    });
    const data = await res.json();
    if(data.error){
      result.innerHTML = '<div class="empty"><div class="empty-icon">❌</div><div>'+data.error+'</div></div>';
      return;
    }
    renderDeepAnalysis(data);
  } catch(err){
    result.innerHTML = '<div class="empty"><div class="empty-icon">⚠️</div><div>Không kết nối được server</div></div>';
  }
}

function renderDeepAnalysis(data){
  const s = data.stock || {};
  const v = data.valuation || {};
  const ind = data.industry || {};
  const roe = data.roe_analysis || {};
  const dup = roe.dupont || {};
  const cmp = roe.compare || {};
  const dv = data.deep_valuation || {};
  const methods = dv.methods || {};
  const fair = dv.fair_range || {};

  const fmtN = (n, u='') => (n==null||isNaN(n)) ? '—' : Number(n).toLocaleString('vi-VN')+u;
  const fmtP = (n) => (n==null) ? '—' : (Number(n)*100).toFixed(2)+'%';

  const verdictMap = {
    'undervalued': {t:'ĐỊNH GIÁ THẤP', c:'sv-g'},
    'slightly_undervalued': {t:'Hơi dưới giá trị', c:'sv-g'},
    'fair': {t:'Đúng giá trị', c:'sv-y'},
    'slightly_overvalued': {t:'Hơi cao hơn giá trị', c:'sv-r'},
    'overvalued': {t:'ĐỊNH GIÁ CAO', c:'sv-r'},
  };
  const vd = verdictMap[dv.verdict] || {t:'Chưa đủ dữ liệu', c:''};

  const roeVerdictMap = {
    'outperform': {t:'VƯỢT TRỘI NGÀNH', c:'sv-g'},
    'above_avg': {t:'Trên trung bình ngành', c:'sv-g'},
    'slightly_below': {t:'Dưới nhẹ trung bình', c:'sv-y'},
    'underperform': {t:'THUA KÉM NGÀNH', c:'sv-r'},
  };
  const rv = roeVerdictMap[cmp.verdict] || {t:'Chưa xác định', c:''};

  let html = '';

  html += '<div style="background:var(--primary-bg);padding:22px;border-radius:12px;margin-bottom:20px;border:1px solid var(--primary-bg-hover);">';
  html += '<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;align-items:center;">';
  html += '<div><span style="font-weight:700;color:var(--primary);font-size:26px;font-family:var(--font-mono);">'+data.symbol+'</span>';
  html += '<span style="color:var(--text-secondary);font-size:13px;margin-left:12px;">'+ (ind.group||'N/A') +' · '+ (s.exchange||'') +'</span></div>';
  html += '<div style="font-size:14px;font-family:var(--font-mono);">Giá: <b>'+fmtN(s.close)+' đ</b>';
  const pct = s.pct || 0;
  const c = pct>0?'up':(pct<0?'down':'ref');
  html += '<span class="'+c+'" style="margin-left:12px;font-weight:700;">'+(pct>0?'+':'')+pct.toFixed(2)+'%</span></div>';
  html += '</div></div>';

  if(data.scoring){
    var sc = data.scoring;
    var scCls = {'positive':'sv-g','neutral':'sv-y','negative':'sv-r'}[sc.label] || '';
    var scIcon = {'positive':'✅','neutral':'⚪','negative':'❌'}[sc.label] || '⚪';
    html += '<h3 style="color:var(--primary);margin:20px 0 14px;font-size:15px;font-weight:700;">'+scIcon+' Chấm Điểm Tổng Hợp</h3>';
    html += '<div class="tcard" style="border-left:4px solid var(--primary);">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">';
    html += '<span style="font-weight:700;">Kết luận: <span class="'+scCls+'">'+sc.label_vn+'</span></span>';
    html += '<span style="font-size:20px;font-weight:700;font-family:var(--font-mono);" class="'+scCls+'">'+(sc.total>0?'+':'')+sc.total+'</span>';
    html += '</div>';
    var parts = sc.parts || {};
    var partLabels = {'technical':'📉 Kỹ thuật','fundamental':'💼 Cơ bản','valuation':'💰 Định giá','news':'📰 Tin tức'};
    for(var k in parts){
      if(!parts[k]) continue;
      var p = parts[k];
      var pCls = p.score > 0 ? 'sv-g' : (p.score < 0 ? 'sv-r' : 'sv-y');
      var pIcon = p.score > 0 ? '✅' : (p.score < 0 ? '❌' : '⚪');
      html += '<div style="padding:8px 0;border-bottom:1px solid var(--border);">';
      html += '<div style="display:flex;justify-content:space-between;"><span style="font-weight:600;">'+pIcon+' '+(partLabels[k]||k)+'</span>';
      html += '<span class="'+pCls+'" style="font-weight:700;font-family:var(--font-mono);">'+(p.score>0?'+':'')+p.score+'</span></div>';
      html += '<div style="font-size:12px;color:var(--text-secondary);margin-top:4px;">'+p.reason+'</div>';
      html += '</div>';
    }
    html += '</div>';
  }

html += '<h3 style="color:var(--primary);margin:20px 0 14px;font-size:15px;font-weight:700;">💰 Định Giá</h3>';
  html += '<div class="m-grid" style="margin-bottom:16px;">';
  html += '<div class="m-item"><div class="m-lb">P/E hiện tại</div><div class="m-vl">'+(v.pe?v.pe+'x':'—')+'</div></div>';
  html += '<div class="m-item"><div class="m-lb">P/B hiện tại</div><div class="m-vl">'+(v.pb?v.pb+'x':'—')+'</div></div>';
  html += '<div class="m-item"><div class="m-lb">EPS</div><div class="m-vl">'+fmtN(v.eps)+'</div></div>';
  html += '<div class="m-item"><div class="m-lb">BVPS</div><div class="m-vl">'+fmtN(v.bvps)+'</div></div>';
  html += '</div>';

  const methodKeys = Object.keys(methods);
  if(methodKeys.length > 0){
    html += '<div class="tcard" style="border-left:4px solid var(--primary);">';
    html += '<div style="font-weight:700;color:var(--primary);margin-bottom:12px;">📐 Định giá theo phương pháp</div>';
    html += '<table style="width:100%;font-size:13px;">';
    methodKeys.forEach(k => {
      const m = methods[k];
      html += '<tr><td>'+m.label+'</td><td class="num" style="font-weight:700;">'+fmtN(m.value)+' đ</td></tr>';
    });
    if(fair.median){
      html += '<tr style="border-top:2px solid var(--border);"><td style="font-weight:700;">Vùng giá hợp lý</td>'+
              '<td class="num" style="font-weight:700;color:var(--primary);">'+
              fmtN(fair.min)+' – '+fmtN(fair.max)+' đ</td></tr>';
      html += '<tr><td style="font-weight:700;">Trung vị</td><td class="num" style="font-weight:700;color:var(--primary);">'+fmtN(fair.median)+' đ</td></tr>';
    }
    html += '</table></div>';
  }

  if(dv.upside_pct != null){
    const upCls = dv.upside_pct > 0 ? 'sv-g' : 'sv-r';
    html += '<div class="tcard" style="background:var(--bg-soft);">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;">';
    html += '<div><div class="m-lb">Upside so với giá hiện tại</div>';
    html += '<div class="m-vl '+upCls+'" style="font-size:22px;">'+(dv.upside_pct>0?'+':'')+dv.upside_pct.toFixed(1)+'%</div></div>';
    html += '<div style="text-align:right;"><div class="m-lb">Kết luận định giá</div>';
    html += '<div class="m-vl '+vd.c+'" style="font-size:16px;">'+vd.t+'</div></div>';
    html += '</div></div>';
  }

  if(dup && !dup.error){
    html += '<h3 style="color:var(--primary);margin:24px 0 14px;font-size:15px;font-weight:700;">📊 Phân Tích ROE — Dupont</h3>';
    html += '<div class="m-grid" style="margin-bottom:14px;">';
    html += '<div class="m-item"><div class="m-lb">ROE hiện tại</div><div class="m-vl sv-g" style="font-size:18px;">'+fmtP(dup.roe_3layer)+'</div></div>';
    if(dup.roe_5layer) html += '<div class="m-item"><div class="m-lb">ROE (Dupont 5 lớp)</div><div class="m-vl">'+fmtP(dup.roe_5layer)+'</div></div>';
    html += '<div class="m-item"><div class="m-lb">Biên LN ròng</div><div class="m-vl">'+fmtP(dup.net_margin)+'</div></div>';
    html += '<div class="m-item"><div class="m-lb">Vòng quay TS</div><div class="m-vl">'+(dup.asset_turnover||'—')+'x</div></div>';
    html += '<div class="m-item"><div class="m-lb">Đòn bẩy</div><div class="m-vl">'+(dup.equity_multiplier||'—')+'x</div></div>';
    if(dup.interest_burden) html += '<div class="m-item"><div class="m-lb">Interest burden</div><div class="m-vl">'+dup.interest_burden+'</div></div>';
    html += '</div>';

    const nm = dup.net_margin || 0;
    const at = dup.asset_turnover || 0;
    const em = dup.equity_multiplier || 0;
    html += '<div class="tcard"><div style="font-weight:700;color:var(--primary);margin-bottom:12px;">🔍 Bóc tách nguồn gốc ROE</div>';
    html += '<div style="font-size:13px;color:var(--text-secondary);margin-bottom:6px;">Biên LN ròng: <b>'+fmtP(nm)+'</b></div>';
    html += '<div class="roe-bar"><div class="roe-fill" style="width:'+Math.min(100, nm*400)+'%;"></div></div>';
    html += '<div style="font-size:13px;color:var(--text-secondary);margin:12px 0 6px;">Vòng quay tài sản: <b>'+at.toFixed(2)+'x</b></div>';
    html += '<div class="roe-bar"><div class="roe-fill" style="width:'+Math.min(100, at*50)+'%;"></div></div>';
    html += '<div style="font-size:13px;color:var(--text-secondary);margin:12px 0 6px;">Đòn bẩy: <b>'+em.toFixed(2)+'x</b></div>';
    html += '<div class="roe-bar"><div class="roe-fill" style="width:'+Math.min(100, em*25)+'%;"></div></div>';
    html += '</div>';
  } else if(dup && dup.error){
    html += '<div class="tcard" style="background:var(--amber-bg);border-color:var(--amber-border);">⚠️ Dupont: '+dup.error+'</div>';
  }

    if(data.risk){
    html += renderRiskSection(data.risk);
  }

  if(data.trade_plan){
    var tp = data.trade_plan;
    var confidenceColor = {'Cao':'sv-g','Trung bình':'sv-y','Thấp':'sv-r'}[tp.confidence] || '';
    var adviceColor = tp.advice.indexOf('MUA')>=0 ? 'sv-g' : (tp.advice.indexOf('KHÔNG')>=0||tp.advice.indexOf('HẠN CHẾ')>=0 ? 'sv-r' : 'sv-y');
    html += '<h3 style="color:var(--primary);margin:24px 0 14px;font-size:15px;font-weight:700;">📋 Kế Hoạch Giao Dịch Tham Khảo</h3>';
    html += '<div class="tcard">';
    html += '<div class="m-grid">';
    html += '<div class="m-item"><div class="m-lb">Vùng vào lệnh</div><div class="m-vl">'+fmtN(tp.entry_low)+' - '+fmtN(tp.entry_high)+' đ</div></div>';
    html += '<div class="m-item"><div class="m-lb">Mục tiêu</div><div class="m-vl sv-g">'+fmtN(tp.target)+' đ ('+(tp.upside_pct>0?'+':'')+tp.upside_pct+'%)</div></div>';
    html += '<div class="m-item"><div class="m-lb">Cắt lỗ</div><div class="m-vl sv-r">'+fmtN(tp.stop)+' đ ('+tp.downside_pct+'%)</div></div>';
    html += '<div class="m-item"><div class="m-lb">R:R</div><div class="m-vl">'+(tp.rr_ratio||'—')+'</div></div>';
    html += '<div class="m-item"><div class="m-lb">Độ tin cậy</div><div class="m-vl '+confidenceColor+'">'+tp.confidence+'</div></div>';
    html += '</div>';
    html += '<div style="margin-top:12px;padding:12px;border-radius:8px;font-weight:700;text-align:center;" class="'+adviceColor+'">'+tp.advice+'</div>';
    html += '</div>';
  }

if(cmp && !cmp.error){
    html += '<h3 style="color:var(--primary);margin:24px 0 14px;font-size:15px;font-weight:700;">🏢 So Sánh ROE Với Ngành</h3>';
    html += '<div class="tcard">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">';
    html += '<span style="font-weight:700;">Ngành: '+cmp.industry_group+'</span>';
    html += '<span class="m-vl '+rv.c+'" style="font-size:15px;">'+rv.t+'</span></div>';
    html += '<div class="m-grid">';
    html += '<div class="m-item"><div class="m-lb">ROE '+data.symbol+'</div><div class="m-vl sv-g">'+fmtN(cmp.stock_roe, '%')+'</div></div>';
    html += '<div class="m-item"><div class="m-lb">TB ngành</div><div class="m-vl">'+fmtN(cmp.industry_avg_roe, '%')+'</div></div>';
    html += '<div class="m-item"><div class="m-lb">Cao nhất ngành</div><div class="m-vl sv-g">'+fmtN(cmp.industry_max_roe, '%')+'</div></div>';
    html += '<div class="m-item"><div class="m-lb">Thấp nhất ngành</div><div class="m-vl sv-r">'+fmtN(cmp.industry_min_roe, '%')+'</div></div>';
    html += '<div class="m-item"><div class="m-lb">Chênh lệch vs TB</div><div class="m-vl '+(cmp.diff_vs_avg>0?'sv-g':'sv-r')+'">'+(cmp.diff_vs_avg>0?'+':'')+cmp.diff_vs_avg+'%</div></div>';
    html += '<div class="m-item"><div class="m-lb">Số mã so sánh</div><div class="m-vl">'+cmp.industry_count+'</div></div>';
    html += '</div></div>';
  } else if(cmp && cmp.error){
    html += '<div class="tcard" style="background:var(--amber-bg);border-color:var(--amber-border);">⚠️ So sánh ngành: '+cmp.error+'</div>';
  }

  // Khuyen nghi CTCK
  if(data.ctck && data.ctck.found){
    html += renderCtckSection(data.ctck, data.symbol);
  }

  if(roe.commentary){
    html += '<h3 style="color:var(--primary);margin:24px 0 14px;font-size:15px;font-weight:700;">📝 Nhận Xét Tự Động</h3>';
    html += '<div class="ai-box">'+roe.commentary+'</div>';
  }

  if(data.report){
    html += '<h3 style="color:var(--primary);margin:24px 0 14px;font-size:15px;font-weight:700;">🤖 Báo Cáo Chuyên Gia AI</h3>';
    html += '<div class="ai-box">'+renderMarkdown(data.report)+'</div>';
  } else if(data.error){
    html += '<div class="tcard" style="background:var(--red-bg);border-color:var(--red-border);">❌ '+data.error+'</div>';
  }

  document.getElementById('deepResult').innerHTML = html;
}

function escapeHtml(s){
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function _inlineMd(s){
  return s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
          .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
}

function _parseMdTable(block){
  var lines = block.trim().split('\n').map(function(l){return l.trim();}).filter(function(l){return l;});
  if(lines.length < 2) return block;
  if(!/^\|[\s\-:|]+\|$/.test(lines[1])) return block;
  var head = lines[0].split('|').slice(1, -1).map(function(c){return _inlineMd(c.trim());});
  var rows = lines.slice(2).map(function(line){
    return line.split('|').slice(1, -1).map(function(c){return _inlineMd(c.trim());});
  });
  var html = '<table class="md-table"><thead><tr>';
  html += head.map(function(c){return '<th>'+c+'</th>';}).join('');
  html += '</tr></thead><tbody>';
  rows.forEach(function(r){
    html += '<tr>' + r.map(function(c){return '<td>'+c+'</td>';}).join('') + '</tr>';
  });
  html += '</tbody></table>';
  return html;
}

function renderMarkdown(md){
  if(!md) return '';
  var h = escapeHtml(md);
  h = h.replace(/((?:^\|.+\|\s*$\n?)+)/gm, function(m){ return _parseMdTable(m); });
  h = h.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  h = h.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  h = h.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  h = h.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  h = h.replace(/^---+$/gm, '<hr>');
  h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  h = h.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
  h = h.replace(/^- (.+)$/gm, '<li>$1</li>');
  h = h.replace(/(<li>[\s\S]*?<\/li>)(?!\s*<li>)/g, '<ul>$1</ul>');
  h = h.replace(/\n{2,}/g, '</p><p>');
  h = h.replace(/\n/g, '<br>');
  h = '<p>' + h + '</p>';
  h = h.replace(/<p>\s*<\/p>/g, '');
  h = h.replace(/<p>(<h[1-4])/g, '$1').replace(/(<\/h[1-4]>)<\/p>/g, '$1');
  h = h.replace(/<p>(<ul>)/g, '$1').replace(/(<\/ul>)<\/p>/g, '$1');
  h = h.replace(/<p>(<hr>)<\/p>/g, '$1');
  h = h.replace(/<p>(<table)/g, '$1').replace(/(<\/table>)<\/p>/g, '$1');
  return h;
}


function fmtVND(n){return n==null||isNaN(n)?'—':Number(n).toLocaleString('vi-VN');}
function fmtVol(n){
  if(!n||isNaN(n))return '—';
  n=Number(n);const sg=n<0?'-':'';n=Math.abs(n);
  if(n>=1e9)return sg+(n/1e9).toFixed(2)+'B';
  if(n>=1e6)return sg+(n/1e6).toFixed(2)+'M';
  if(n>=1e3)return sg+(n/1e3).toFixed(1)+'K';
  return sg+n.toString();
}
function toggleTheme(){
  document.body.classList.toggle('light');
  document.getElementById('themeBtn').textContent=document.body.classList.contains('light')?'🌙':'☀️';
}
function updateClock(){document.getElementById('clock').textContent=new Date().toLocaleTimeString('vi-VN');}
function showToast(msg){
  const t = document.getElementById('toast');
  if(!t){console.log('Toast:', msg);return;}
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}

async function fetchRealtimePrices(silent){
  if(window._isFetching) return;
  window._isFetching = true;
  const btn = document.getElementById('refreshBtn');
  if(!silent && btn){btn.textContent = '⏳';btn.style.opacity = '0.6';}
  try {
    const res = await fetch('http://localhost:5000/api/prices');
    const data = await res.json();
    if(data.error){console.error('Loi fetch gia:', data.error);return;}
    const stocks = data.stocks || [];
    if(stocks.length === 0){console.warn('Khong co gia moi');return;}
    const stockMap = {};
    stocks.forEach(s => { stockMap[s.symbol] = s; });
    let updatedCount = 0;
    for(let i = 0; i < STOCK_DATA.length; i++){
      const sym = STOCK_DATA[i].symbol;
      if(stockMap[sym]){
        Object.assign(STOCK_DATA[i], stockMap[sym]);
        updatedCount++;
      }
    }
    const lastEl = document.getElementById('lastUpdate');
    if(lastEl && data.updated) lastEl.textContent = data.updated;
    renderTable();
    document.getElementById('sUp').textContent = STOCK_DATA.filter(s=>s.pct>0).length;
    document.getElementById('sDown').textContent = STOCK_DATA.filter(s=>s.pct<0).length;
    document.getElementById('sRef').textContent = STOCK_DATA.filter(s=>s.pct===0).length;
    console.log('[REALTIME] Cap nhat', updatedCount, 'ma trong', data.elapsed_seconds, 'giay');
    if(!silent) showToast('✅ Đã cập nhật giá (' + data.elapsed_seconds + 's)');
  } catch(err){
    console.error('Loi fetch gia:', err);
    if(!silent) showToast('❌ Không kết nối được server');
  } finally {
    window._isFetching = false;
    if(btn){btn.textContent = '🔄';btn.style.opacity = '1';}
  }
}

async function fullRefresh(){
  if(!confirm('Cập nhật TOÀN BỘ dữ liệu (giá + tin tức + báo cáo + PDF)?\n\nMất ~5 phút. Bạn vẫn dùng được web.')) return;
  document.getElementById('progressModal').classList.add('active');
  document.getElementById('progressBar').style.width = '0%';
  document.getElementById('progressPercent').textContent = '0%';
  document.getElementById('progressStep').textContent = 'Đang khởi động...';
  document.getElementById('progressIcon').textContent = '⚡';
  try {
    await fetch('http://localhost:5000/api/refresh', {method: 'POST'});
    pollFullRefresh();
  } catch(err){
    alert('Không kết nối được server');
    closeProgressModal();
  }
}

let _pollInterval = null;

function closeProgressModal(){
  document.getElementById('progressModal').classList.remove('active');
  if(_pollInterval){clearInterval(_pollInterval);_pollInterval = null;}
}

function pollFullRefresh(){
  if(_pollInterval) clearInterval(_pollInterval);
  _pollInterval = setInterval(async () => {
    try {
      const res = await fetch('http://localhost:5000/api/status');
      const data = await res.json();
      const percent = data.percent || 0;
      const step = data.step || 'Đang xử lý...';
      const isRunning = data.is_running;
      document.getElementById('progressBar').style.width = percent + '%';
      document.getElementById('progressPercent').textContent = percent + '%';
      document.getElementById('progressStep').textContent = step;
      if(!isRunning && percent >= 100){
        document.getElementById('progressIcon').textContent = '✅';
        document.getElementById('progressStep').textContent = 'Hoàn tất! Đang reload...';
        clearInterval(_pollInterval);
        _pollInterval = null;
        setTimeout(() => {location.reload();}, 1000);
      } else if(!isRunning && data.error){
        document.getElementById('progressIcon').textContent = '❌';
        document.getElementById('progressStep').textContent = 'Lỗi: ' + data.error;
        clearInterval(_pollInterval);
        _pollInterval = null;
      }
    } catch(err){console.error('Poll status loi:', err);}
  }, 2000);
}

setInterval(() => {
  if(document.hidden || document.visibilityState !== 'visible') return;
  if(currentTab === 'deep-analyze' || currentTab === 'chat-ai') return;
  fetchRealtimePrices(true);
}, 60000);

document.addEventListener('visibilitychange', () => {
  if(document.visibilityState === 'visible'){
    if(currentTab === 'deep-analyze' || currentTab === 'chat-ai') return;
    if(Date.now() - (window._lastFetchTime || 0) > 60000){
      fetchRealtimePrices(true);
    }
  }
});

// ============================================================
// SCREENER
// ============================================================
function _getIndustryOf(sym){
  var ind = INDUSTRY_DATA[sym];
  return ind ? (ind.group || 'Khác') : 'Khác';
}

function _getSentimentOf(sym){
  // Tim tin tuc co chua ma trong tieu de/desc
  if(!RSS_NEWS || RSS_NEWS.length === 0) return 'neutral';
  var matched = RSS_NEWS.filter(function(n){
    var t = (n.title || '').toUpperCase();
    return t.indexOf(sym) >= 0;
  });
  if(matched.length === 0) return 'neutral';
  var pos = matched.filter(function(n){ return n.sentiment_label === 'positive'; }).length;
  var neg = matched.filter(function(n){ return n.sentiment_label === 'negative'; }).length;
  if(pos > neg) return 'positive';
  if(neg > pos) return 'negative';
  return 'neutral';
}

function initScreenerIndustry(){
  var sel = document.getElementById('scIndustry');
  if(!sel) return;
  var industries = {};
  Object.values(INDUSTRY_DATA).forEach(function(ind){
    var g = ind.group || 'Khác';
    industries[g] = (industries[g] || 0) + 1;
  });
  var keys = Object.keys(industries).sort();
  sel.innerHTML = '<option value="">Tất cả ngành (' + STOCK_DATA.length + ')</option>';
  keys.forEach(function(k){
    sel.innerHTML += '<option value="' + k + '">' + k + ' (' + industries[k] + ')</option>';
  });
}

function applyScreener(){
  currentPage = 1;
  renderTable();
}

function resetScreener(){
  document.getElementById('scSymbol').value = '';
  document.getElementById('scIndustry').value = '';
  document.getElementById('scPeMin').value = '';
  document.getElementById('scPeMax').value = '';
  document.getElementById('scRoeMin').value = '';
  document.getElementById('scSentiment').value = '';
  document.getElementById('scSignal').value = '';
  document.getElementById('search').value = '';
  applyScreener();
}

function _filteredByScreener(){
  var sym = (document.getElementById('scSymbol').value || '').toUpperCase().trim();
  var ind = document.getElementById('scIndustry').value;
  var peMin = parseFloat(document.getElementById('scPeMin').value);
  var peMax = parseFloat(document.getElementById('scPeMax').value);
  var roeMin = parseFloat(document.getElementById('scRoeMin').value);
  var sent = document.getElementById('scSentiment').value;
  var sig = document.getElementById('scSignal').value;

  return STOCK_DATA.filter(function(s){
    var v = VALUATION_DATA[s.symbol] || {};
    var ta = TECHNICAL_DATA[s.symbol] || {};

    if(sym && s.symbol.indexOf(sym) < 0) return false;
    if(ind && _getIndustryOf(s.symbol) !== ind) return false;

    if(!isNaN(peMin)){
      if(v.pe == null || v.pe < peMin) return false;
    }
    if(!isNaN(peMax)){
      if(v.pe == null || v.pe > peMax) return false;
    }
    if(!isNaN(roeMin)){
      if(v.roe == null || v.roe < roeMin) return false;
    }
    if(sent && _getSentimentOf(s.symbol) !== sent) return false;
    if(sig && ta.signal !== sig) return false;
    return true;
  });
}

function exportCSV(){
  var data = _filteredByScreener();
  if(data.length === 0){ alert('Không có mã nào để xuất'); return; }
  var rows = [['Mã','Sàn','Giá','%Thay đổi','KL','P/E','P/B','ROE(%)','ROA(%)','Ngành','Tin tức','Kỹ thuật']];
  data.forEach(function(s){
    var v = VALUATION_DATA[s.symbol] || {};
    var ta = TECHNICAL_DATA[s.symbol] || {};
    var sent = _getSentimentOf(s.symbol);
    var sentVN = {'positive':'Tích cực','negative':'Tiêu cực','neutral':'Trung lập'}[sent] || 'Trung lập';
    rows.push([
      s.symbol,
      s.exchange || '',
      s.close || '',
      (s.pct||0).toFixed(2),
      s.volume || 0,
      v.pe || '',
      v.pb || '',
      v.roe || '',
      v.roa || '',
      _getIndustryOf(s.symbol),
      sentVN,
      ta.signal || '',
    ]);
  });
  var csv = rows.map(function(r){
    return r.map(function(c){
      var s = String(c == null ? '' : c);
      if(s.indexOf(',') >= 0 || s.indexOf('"') >= 0){
        return '"' + s.replace(/"/g, '""') + '"';
      }
      return s;
    }).join(',');
  }).join('\n');
  var blob = new Blob(['\ufeff' + csv], {type:'text/csv;charset=utf-8'});
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download = 'screener_' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
  URL.revokeObjectURL(url);
}


// ============================================================
// WATCHLIST
// ============================================================
var _watchlistCache = [];

async function loadWatchlist(){
  try {
    var res = await fetch('http://localhost:5000/api/watchlist');
    var data = await res.json();
    _watchlistCache = data.items || [];
    _updateStarButtons();
  } catch(err){
    console.warn('[Watchlist] Loi load:', err);
  }
}

function isWatched(sym){
  return _watchlistCache.some(function(w){ return w.symbol === sym; });
}

function _updateStarButtons(){
  document.querySelectorAll('.wl-btn').forEach(function(btn){
    var sym = btn.getAttribute('data-sym');
    if(isWatched(sym)){
      btn.classList.add('active');
      btn.innerHTML = '★';
      btn.title = 'Bỏ khỏi danh mục';
    } else {
      btn.classList.remove('active');
      btn.innerHTML = '☆';
      btn.title = 'Thêm vào danh mục';
    }
  });
}

async function toggleWatchlist(sym, ev){
  if(ev){ ev.stopPropagation(); ev.preventDefault(); }
  sym = sym.toUpperCase();
  try {
    if(isWatched(sym)){
      var res = await fetch('http://localhost:5000/api/watchlist/' + sym, { method: 'DELETE' });
      var data = await res.json();
      if(data.ok){
        _watchlistCache = _watchlistCache.filter(function(w){ return w.symbol !== sym; });
        showToast('🗑️ Đã bỏ ' + sym);
      }
    } else {
      var res2 = await fetch('http://localhost:5000/api/watchlist', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({symbol: sym})
      });
      var data2 = await res2.json();
      if(data2.ok){
        _watchlistCache.push({symbol: sym, added_at: new Date().toLocaleString('vi-VN'), note: '', target_price: null, stop_price: null});
        showToast('⭐ Đã thêm ' + sym);
      }
    }
    _updateStarButtons();
    if(currentTab === 'watchlist') renderWatchlist();
  } catch(err){
    showToast('❌ Lỗi kết nối');
  }
}

async function addToWatchlist(){
  var inp = document.getElementById('wlAddSymbol');
  var sym = (inp.value || '').trim().toUpperCase();
  if(!sym){ alert('Nhập mã cổ phiếu'); return; }
  if(isWatched(sym)){ alert(sym + ' đã có trong danh mục'); return; }
  try {
    var res = await fetch('http://localhost:5000/api/watchlist', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({symbol: sym})
    });
    var data = await res.json();
    if(data.ok){
      _watchlistCache.push({symbol: sym, added_at: new Date().toLocaleString('vi-VN'), note: '', target_price: null, stop_price: null});
      inp.value = '';
      showToast('⭐ Đã thêm ' + sym);
      _updateStarButtons();
      renderWatchlist();
    } else {
      alert(data.error || 'Không thêm được');
    }
  } catch(err){
    alert('Lỗi kết nối server');
  }
}

async function removeFromWatchlist(sym, ev){
  if(ev){ ev.stopPropagation(); }
  if(!confirm('Bỏ ' + sym + ' khỏi danh mục?')) return;
  try {
    var res = await fetch('http://localhost:5000/api/watchlist/' + sym, { method: 'DELETE' });
    var data = await res.json();
    if(data.ok){
      _watchlistCache = _watchlistCache.filter(function(w){ return w.symbol !== sym; });
      showToast('🗑️ Đã bỏ ' + sym);
      _updateStarButtons();
      renderWatchlist();
    }
  } catch(err){
    alert('Lỗi kết nối');
  }
}

function renderWatchlist(){
  var el = document.getElementById('wlList');
  var countEl = document.getElementById('wlCount');
  if(!el) return;
  if(countEl) countEl.textContent = 'Tổng: ' + _watchlistCache.length + ' mã';
  if(_watchlistCache.length === 0){
    el.innerHTML = '<div class="empty"><div class="empty-icon">⭐</div><div>Chưa có mã nào trong danh mục</div><div style="font-size:12px;margin-top:8px;color:var(--text-muted);">Bấm ngôi sao ☆ ở bảng Cổ Phiếu hoặc nhập mã ở trên</div></div>';
    return;
  }
  var html = '';
  _watchlistCache.forEach(function(w){
    var s = STOCK_DATA.find(function(x){ return x.symbol === w.symbol; }) || {};
    var v = VALUATION_DATA[w.symbol] || {};
    var ta = TECHNICAL_DATA[w.symbol] || {};
    var ind = INDUSTRY_DATA[w.symbol] || {};
    var pct = s.pct || 0;
    var pctCls = pct > 0 ? 'up' : (pct < 0 ? 'down' : 'ref');
    var sigCls = ta.signal === 'Tăng' ? 'up' : (ta.signal === 'Giảm' ? 'down' : 'ref');
    html += '<div class="wl-card" onclick="openModal(\'' + w.symbol + '\')">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">';
    html += '<div><span class="wl-symbol">' + w.symbol + '</span>';
    html += '<span class="exch" style="margin-left:8px;">' + (s.exchange || '') + '</span>';
    html += '<span style="color:var(--text-muted);font-size:12px;margin-left:10px;">' + (ind.group || '') + '</span></div>';
    html += '<button class="wl-remove" onclick="removeFromWatchlist(\'' + w.symbol + '\', event)">🗑️ Bỏ</button>';
    html += '</div>';
    html += '<div class="wl-meta">';
    html += '<div class="wl-meta-item"><span class="wl-meta-label">Giá:</span><span class="wl-meta-value ' + pctCls + '">' + (s.close ? Number(s.close).toLocaleString('vi-VN') : '—') + ' (' + (pct > 0 ? '+' : '') + pct.toFixed(2) + '%)</span></div>';
    html += '<div class="wl-meta-item"><span class="wl-meta-label">P/E:</span><span class="wl-meta-value">' + (v.pe || '—') + '</span></div>';
    html += '<div class="wl-meta-item"><span class="wl-meta-label">P/B:</span><span class="wl-meta-value">' + (v.pb || '—') + '</span></div>';
    html += '<div class="wl-meta-item"><span class="wl-meta-label">ROE:</span><span class="wl-meta-value">' + (v.roe ? v.roe + '%' : '—') + '</span></div>';
    html += '<div class="wl-meta-item"><span class="wl-meta-label">Kỹ thuật:</span><span class="wl-meta-value ' + sigCls + '">' + (ta.signal || '—') + '</span></div>';
    if(ta.trade_plan && ta.trade_plan.target){
      html += '<div class="wl-meta-item"><span class="wl-meta-label">Mục tiêu:</span><span class="wl-meta-value sv-g">' + Number(ta.trade_plan.target).toLocaleString('vi-VN') + '</span></div>';
    }
    html += '</div>';
    if(w.added_at){
      html += '<div style="margin-top:8px;font-size:11px;color:var(--text-muted);font-family:var(--font-mono);">📅 Thêm: ' + w.added_at + '</div>';
    }
    html += '</div>';
  });
  el.innerHTML = html;
}


// ============================================================
// CTCK RECOMMENDATIONS
// ============================================================
async function loadCtckFor(symbol){
  try {
    var res = await fetch('http://localhost:5000/api/ctck/' + symbol);
    var data = await res.json();
    return data;
  } catch(err){
    console.warn('[CTCK] Loi load:', err);
    return null;
  }
}

function renderCtckSection(info, sym){
  if(!info || !info.found || !info.recommendations || info.recommendations.length === 0){
    return '';
  }
  var html = '<h3 style="color:var(--primary);margin:24px 0 14px;font-size:15px;font-weight:700;">🏢 Khuyến Nghị Từ CTCK</h3>';
  html += '<div class="tcard">';

  // Summary
  html += '<div class="m-grid" style="margin-bottom:14px;">';
  var avgT = info.avg_target ? Number(info.avg_target).toLocaleString('vi-VN') + ' đ' : '—';
  var maxT = info.max_target ? Number(info.max_target).toLocaleString('vi-VN') + ' đ' : '—';
  var minT = info.min_target ? Number(info.min_target).toLocaleString('vi-VN') + ' đ' : '—';
  html += '<div class="m-item"><div class="m-lb">Giá mục tiêu TB</div><div class="m-vl sv-g">'+avgT+'</div></div>';
  html += '<div class="m-item"><div class="m-lb">Cao nhất</div><div class="m-vl">'+maxT+'</div></div>';
  html += '<div class="m-item"><div class="m-lb">Thấp nhất</div><div class="m-vl">'+minT+'</div></div>';
  html += '<div class="m-item"><div class="m-lb">Số CTCK</div><div class="m-vl">'+info.total_reports+'</div></div>';
  html += '</div>';

  // Reco count
  html += '<div style="display:flex;gap:12px;margin-bottom:14px;">';
  if(info.buy_count > 0) html += '<span class="sent-badge sent-pos">✅ MUA: '+info.buy_count+'</span>';
  if(info.hold_count > 0) html += '<span class="sent-badge sent-neu">⚪ NẮM GIỮ: '+info.hold_count+'</span>';
  if(info.sell_count > 0) html += '<span class="sent-badge sent-neg">❌ BÁN: '+info.sell_count+'</span>';
  html += '</div>';

  // Table
  html += '<table style="width:100%;font-size:12px;border-collapse:collapse;">';
  html += '<thead><tr style="background:var(--bg-soft);">'
       + '<th style="text-align:left;padding:8px;border-bottom:1px solid var(--border);">CTCK</th>'
       + '<th style="text-align:left;padding:8px;border-bottom:1px solid var(--border);">Ngày</th>'
       + '<th style="text-align:right;padding:8px;border-bottom:1px solid var(--border);">Giá MT</th>'
       + '<th style="text-align:center;padding:8px;border-bottom:1px solid var(--border);">Khuyến nghị</th>'
       + '<th style="text-align:center;padding:8px;border-bottom:1px solid var(--border);">Báo cáo</th>'
       + '</tr></thead><tbody>';

  info.recommendations.forEach(function(r){
    var recoColor = 'var(--text-muted)';
    var recoBg = 'var(--bg-soft)';
    if(r.reco === 'MUA MẠNH' || r.reco === 'MUA'){
      recoColor = 'var(--green)'; recoBg = 'var(--green-bg)';
    } else if(r.reco === 'BÁN'){
      recoColor = 'var(--red)'; recoBg = 'var(--red-bg)';
    } else if(r.reco === 'NẮM GIỮ'){
      recoColor = 'var(--amber)'; recoBg = 'var(--amber-bg)';
    }
    html += '<tr>';
    html += '<td style="padding:8px;border-bottom:1px solid var(--border);font-weight:700;">'+r.source+'</td>';
    html += '<td style="padding:8px;border-bottom:1px solid var(--border);font-family:var(--font-mono);">'+(r.date||'—')+'</td>';
    html += '<td style="padding:8px;border-bottom:1px solid var(--border);text-align:right;font-family:var(--font-mono);font-weight:700;">'+(r.target?Number(r.target).toLocaleString('vi-VN'):'—')+'</td>';
    html += '<td style="padding:8px;border-bottom:1px solid var(--border);text-align:center;"><span style="background:'+recoBg+';color:'+recoColor+';padding:3px 8px;border-radius:5px;font-size:10px;font-weight:700;">'+(r.reco||'—')+'</span></td>';
    html += '<td style="padding:8px;border-bottom:1px solid var(--border);text-align:center;"><a href="'+r.url+'" target="_blank" rel="noopener noreferrer" style="color:var(--primary);text-decoration:none;font-size:11px;">🔗 Xem</a></td>';
    html += '</tr>';
  });

  html += '</tbody></table>';
  html += '</div>';
  return html;
}

// ============================================================
// COMPARE 2 STOCKS
// ============================================================
function initCompare(){
  var el = document.getElementById('cmpQuick');
  if(!el) return;
  var quick = [
    ['FPT','CMG'],
    ['VCB','BID'],
    ['HPG','HSG'],
    ['VNM','MSN'],
    ['MWG','PNJ'],
    ['SSI','VND'],
    ['VHM','VIC'],
    ['TCB','MBB'],
  ];
  el.innerHTML = '<span style="color:var(--text-muted);font-size:12px;font-weight:600;">Gợi ý:</span>' +
    quick.map(function(p){
      return '<button onclick="fillCompare(\''+p[0]+'\',\''+p[1]+'\')" style="padding:6px 12px;background:var(--primary-bg);color:var(--primary);border:1px solid var(--primary-bg-hover);border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;font-family:var(--font-mono);">'+p[0]+' vs '+p[1]+'</button>';
    }).join('');
}

function fillCompare(a, b){
  document.getElementById('cmpSym1').value = a;
  document.getElementById('cmpSym2').value = b;
  runCompare();
}

async function runCompare(){
  var s1 = (document.getElementById('cmpSym1').value || '').trim().toUpperCase();
  var s2 = (document.getElementById('cmpSym2').value || '').trim().toUpperCase();
  var result = document.getElementById('cmpResult');

  if(!s1 || !s2){ alert('Nhập đủ 2 mã'); return; }
  if(s1 === s2){ alert('Hai mã không được trùng nhau'); return; }

  result.innerHTML = '<div style="text-align:center;padding:40px;">' +
    '<div style="font-size:36px;margin-bottom:12px;">⏳</div>' +
    '<div style="color:var(--text-secondary);">Đang tải dữ liệu ' + s1 + ' và ' + s2 + '...</div>' +
    '<div style="font-size:12px;color:var(--text-muted);margin-top:8px;">Lần đầu có thể mất 5-10 giây</div>' +
    '</div>';

  try {
    var res = await fetch('http://localhost:5000/api/compare/' + s1 + '/' + s2);
    var data = await res.json();
    if(data.error){
      result.innerHTML = '<div class="empty"><div class="empty-icon">❌</div><div>' + data.error + '</div></div>';
      return;
    }
    renderCompareResult(data);
  } catch(err){
    result.innerHTML = '<div class="empty"><div class="empty-icon">⚠️</div><div>Không kết nối được server</div></div>';
  }
}

function renderCompareResult(data){
  var el = document.getElementById('cmpResult');
  var s1 = data.sym1, s2 = data.sym2;
  var m1 = data.metrics1 || {};
  var m2 = data.metrics2 || {};
  var v1 = data.valuation1 || {};
  var v2 = data.valuation2 || {};

  var fmtN = function(n){ return (n == null || isNaN(n)) ? '—' : Number(n).toLocaleString('vi-VN'); };
  var fmtPct = function(v){ return (v == null) ? '—' : (Number(v)*100).toFixed(2) + '%'; };

  var html = '';

  // Header 2 mã
  html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;">';
  [['1', s1, data.name1, data.industry1, m1, v1],
   ['2', s2, data.name2, data.industry2, m2, v2]].forEach(function(row){
    var idx = row[0], sym = row[1], name = row[2], ind = row[3], m = row[4], v = row[5];
    html += '<div class="tcard" style="border-left:4px solid var(--primary);padding:16px;">';
    html += '<div style="font-weight:700;color:var(--primary);font-size:20px;font-family:var(--font-mono);">' + sym + '</div>';
    if(name) html += '<div style="font-size:12px;color:var(--text-secondary);margin-top:4px;">' + name + '</div>';
    if(ind) html += '<div style="font-size:11px;color:var(--text-muted);margin-top:2px;">🏷️ ' + ind + '</div>';
    html += '<div style="font-size:22px;font-weight:700;font-family:var(--font-mono);margin-top:10px;">' + fmtN(m.close) + ' đ</div>';
    html += '</div>';
  });
  html += '</div>';

  // Bang so sanh dinh luong
  html += '<div class="tcard" style="margin-bottom:20px;">';
  html += '<h3 style="color:var(--primary);margin-bottom:14px;font-size:14px;font-weight:700;">📊 Chỉ Số Định Lượng</h3>';
  html += '<table style="width:100%;font-size:13px;border-collapse:collapse;">';
  html += '<thead><tr style="background:var(--bg-soft);">' +
    '<th style="text-align:left;padding:10px;border-bottom:1px solid var(--border);">Chỉ tiêu</th>' +
    '<th style="text-align:right;padding:10px;border-bottom:1px solid var(--border);">' + s1 + '</th>' +
    '<th style="text-align:right;padding:10px;border-bottom:1px solid var(--border);">' + s2 + '</th>' +
    '<th style="text-align:center;padding:10px;border-bottom:1px solid var(--border);">Ai hơn?</th>' +
    '</tr></thead><tbody>';

  var metrics = [
    {name: 'P/E', v1: v1.pe, v2: v2.pe, better: 'low', fmt: function(x){ return x ? x.toFixed(2) + 'x' : '—'; }},
    {name: 'P/B', v1: v1.pb, v2: v2.pb, better: 'low', fmt: function(x){ return x ? x.toFixed(2) + 'x' : '—'; }},
    {name: 'ROE', v1: v1.roe, v2: v2.roe, better: 'high', fmt: function(x){ return x ? x.toFixed(2) + '%' : '—'; }},
    {name: 'ROA', v1: v1.roa, v2: v2.roa, better: 'high', fmt: function(x){ return x ? x.toFixed(2) + '%' : '—'; }},
    {name: 'Beta', v1: m1.beta, v2: m2.beta, better: 'low', fmt: function(x){ return x == null ? '—' : x.toFixed(2); }},
    {name: 'Độ lệch chuẩn/năm', v1: m1.sigma, v2: m2.sigma, better: 'low', fmt: fmtPct},
    {name: 'CAGR 1 năm', v1: m1.cagr_1y, v2: m2.cagr_1y, better: 'high', fmt: fmtPct},
    {name: 'CAGR 2 năm', v1: m1.cagr_2y, v2: m2.cagr_2y, better: 'high', fmt: fmtPct},
    {name: 'Sharpe Ratio', v1: m1.sharpe, v2: m2.sharpe, better: 'high', fmt: function(x){ return x == null ? '—' : x.toFixed(2); }},
    {name: 'Max Drawdown', v1: m1.max_drawdown, v2: m2.max_drawdown, better: 'high', fmt: fmtPct},
  ];

  metrics.forEach(function(m){
    var better = '';
    if(m.v1 != null && m.v2 != null){
      if(m.better === 'high'){
        if(m.v1 > m.v2) better = '<span style="color:var(--green);font-weight:700;">← ' + s1 + '</span>';
        else if(m.v2 > m.v1) better = '<span style="color:var(--green);font-weight:700;">' + s2 + ' →</span>';
        else better = '<span style="color:var(--text-muted);">Hòa</span>';
      } else {
        if(m.v1 < m.v2) better = '<span style="color:var(--green);font-weight:700;">← ' + s1 + '</span>';
        else if(m.v2 < m.v1) better = '<span style="color:var(--green);font-weight:700;">' + s2 + ' →</span>';
        else better = '<span style="color:var(--text-muted);">Hòa</span>';
      }
    }
    html += '<tr>' +
      '<td style="padding:10px;border-bottom:1px solid var(--border);">' + m.name + '</td>' +
      '<td style="padding:10px;border-bottom:1px solid var(--border);text-align:right;font-family:var(--font-mono);">' + m.fmt(m.v1) + '</td>' +
      '<td style="padding:10px;border-bottom:1px solid var(--border);text-align:right;font-family:var(--font-mono);">' + m.fmt(m.v2) + '</td>' +
      '<td style="padding:10px;border-bottom:1px solid var(--border);text-align:center;font-size:12px;">' + better + '</td>' +
      '</tr>';
  });

  html += '</tbody></table>';
  html += '</div>';

  // Correlation
  if(data.correlation != null){
    var corrText = '';
    if(data.correlation > 0.7) corrText = 'Cao — di chuyển gần như cùng chiều';
    else if(data.correlation > 0.4) corrText = 'Trung bình — có tương quan rõ rệt';
    else if(data.correlation > 0) corrText = 'Thấp — ít tương quan';
    else corrText = 'Âm — di chuyển ngược chiều (đa dạng hóa tốt)';

    html += '<div class="tcard" style="margin-bottom:20px;">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">';
    html += '<div><div style="font-size:12px;color:var(--text-muted);font-weight:700;">HỆ SỐ TƯƠNG QUAN</div>';
    html += '<div style="font-size:28px;font-weight:700;color:var(--primary);font-family:var(--font-mono);">' + data.correlation + '</div></div>';
    html += '<div style="font-size:12px;color:var(--text-secondary);">' + corrText + '</div>';
    html += '</div></div>';
  }

  // Chart
  if(data.chart){
    html += '<div class="tcard" style="margin-bottom:20px;">';
    html += '<h3 style="color:var(--primary);margin-bottom:14px;font-size:14px;font-weight:700;">📈 So Sánh Tăng Trưởng 2 Năm</h3>';
    html += '<div style="text-align:center;"><img src="data:image/png;base64,' + data.chart + '" style="max-width:100%;border-radius:8px;display:block;margin:0 auto;"></div>';
    html += '</div>';
  }

  el.innerHTML = html;
}

// ============================================================
// PORTFOLIO OPTIMIZER
// ============================================================
var _pfItems = [];

function initPortfolio(){
  renderPortfolioItems();
  var inp = document.getElementById('pfSymbol');
  var wInp = document.getElementById('pfWeight');
  if(inp && !inp._init){
    inp._init = true;
    inp.addEventListener('keydown', function(e){
      if(e.key === 'Enter'){ addPortfolioItem(); }
    });
  }
  if(wInp && !wInp._init){
    wInp._init = true;
    wInp.addEventListener('keydown', function(e){
      if(e.key === 'Enter'){ addPortfolioItem(); }
    });
  }
}

function addPortfolioItem(){
  var symEl = document.getElementById('pfSymbol');
  var wEl = document.getElementById('pfWeight');
  if(!symEl || !wEl) return;
  var sym = (symEl.value || '').trim().toUpperCase();
  var w = parseFloat(wEl.value);

  if(!sym){ alert('Nhập mã cổ phiếu'); return; }
  if(isNaN(w) || w <= 0){ alert('Nhập tỷ trọng > 0'); return; }
  if(_pfItems.length >= 12){ alert('Tối đa 12 mã'); return; }
  if(_pfItems.some(function(x){ return x.symbol === sym; })){ alert(sym + ' đã có'); return; }

  _pfItems.push({symbol: sym, weight: w});
  symEl.value = '';
  wEl.value = '';
  symEl.focus();
  renderPortfolioItems();
}

function removePortfolioItem(sym){
  _pfItems = _pfItems.filter(function(x){ return x.symbol !== sym; });
  renderPortfolioItems();
}

function resetPortfolio(){
  if(_pfItems.length === 0 || confirm('Xóa hết danh mục?')){
    _pfItems = [];
    renderPortfolioItems();
    document.getElementById('pfResult').innerHTML = '<div class="empty"><div class="empty-icon">💼</div><div>Thêm 2-12 mã và bấm Tối Ưu</div></div>';
  }
}

function renderPortfolioItems(){
  var el = document.getElementById('pfItems');
  if(!el) return;
  if(_pfItems.length === 0){
    el.innerHTML = '<div style="color:var(--text-muted);font-size:12px;text-align:center;padding:10px;">Chưa có mã nào. Thêm 2-12 mã để tối ưu.</div>';
    return;
  }
  var total = _pfItems.reduce(function(s, x){ return s + x.weight; }, 0);
  var html = '<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">';
  _pfItems.forEach(function(item){
    html += '<div style="display:inline-flex;align-items:center;gap:8px;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px 12px;">'
      + '<span style="font-weight:700;color:var(--primary);font-family:var(--font-mono);">' + item.symbol + '</span>'
      + '<span style="font-weight:600;font-family:var(--font-mono);">' + item.weight + '%</span>'
      + '<button onclick="removePortfolioItem(\'' + item.symbol + '\')" style="background:transparent;border:none;color:var(--red);cursor:pointer;font-size:16px;padding:0 4px;">×</button>'
      + '</div>';
  });
  html += '</div>';
  html += '<div style="margin-top:10px;font-size:12px;color:' + (Math.abs(total - 100) > 0.01 ? 'var(--amber)' : 'var(--green)') + ';font-weight:600;">Tổng: ' + total.toFixed(1) + '% ' + (Math.abs(total - 100) > 0.01 ? '(sẽ tự chuẩn hóa về 100%)' : '✓') + '</div>';
  el.innerHTML = html;
}

async function runPortfolioOptimize(){
  if(_pfItems.length < 2){ alert('Cần ít nhất 2 mã'); return; }
  var rf = parseFloat(document.getElementById('pfRf').value) / 100;
  var maxW = parseFloat(document.getElementById('pfMaxW').value) / 100;
  if(isNaN(rf)) rf = 0.033;
  if(isNaN(maxW) || maxW <= 0 || maxW > 1) maxW = 1.0;

  var result = document.getElementById('pfResult');
  result.innerHTML = '<div style="text-align:center;padding:60px;">'
    + '<div style="font-size:48px;margin-bottom:16px;">⏳</div>'
    + '<div style="color:var(--text-secondary);font-size:15px;font-weight:600;">Đang tối ưu danh mục Markowitz...</div>'
    + '<div style="font-size:12px;color:var(--text-muted);margin-top:8px;">SLSQP + Monte Carlo 5000 danh mục · mất 10-20s</div>'
    + '</div>';

  try {
    var res = await fetch('http://localhost:5000/api/portfolio/optimize', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        holdings: _pfItems.map(function(x){ return {symbol: x.symbol, weight: x.weight}; }),
        rf: rf,
        max_weight: maxW,
        n_mc: 5000,
      }),
    });
    var data = await res.json();
    if(data.error){
      result.innerHTML = '<div class="empty"><div class="empty-icon">❌</div><div>' + data.error + '</div></div>';
      return;
    }
    renderPortfolioResult(data);
  } catch(err){
    result.innerHTML = '<div class="empty"><div class="empty-icon">⚠️</div><div>Không kết nối được server: ' + err.message + '</div></div>';
  }
}

function renderPortfolioResult(data){
  var el = document.getElementById('pfResult');
  var fmtPct = function(v){ return (v == null) ? '—' : (v*100).toFixed(2) + '%'; };

  var html = '';

  // Header: 3 the tong hop
  html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:20px;">';

  // Danh muc hien tai
  html += '<div class="tcard" style="border-left:4px solid var(--purple);">';
  html += '<div style="font-size:11px;color:var(--text-muted);font-weight:700;margin-bottom:6px;">📊 DANH MỤC HIỆN TẠI</div>';
  html += '<div style="font-size:24px;font-weight:700;font-family:var(--font-mono);color:' + (data.current.ret >= 0 ? 'var(--green)' : 'var(--red)') + ';">' + fmtPct(data.current.ret) + '</div>';
  html += '<div style="font-size:12px;color:var(--text-secondary);margin-top:4px;">TSSL kỳ vọng/năm</div>';
  html += '<div style="margin-top:10px;font-size:12px;"><b>σ:</b> ' + fmtPct(data.current.vol) + ' · <b>Sharpe:</b> ' + data.current.sharpe.toFixed(2) + '</div>';
  html += '</div>';

  // Max Sharpe
  if(data.max_sharpe){
    html += '<div class="tcard" style="border-left:4px solid var(--red);">';
    html += '<div style="font-size:11px;color:var(--text-muted);font-weight:700;margin-bottom:6px;">⭐ MAX SHARPE (SLSQP)</div>';
    html += '<div style="font-size:24px;font-weight:700;font-family:var(--font-mono);color:' + (data.max_sharpe.ret >= 0 ? 'var(--green)' : 'var(--red)') + ';">' + fmtPct(data.max_sharpe.ret) + '</div>';
    html += '<div style="font-size:12px;color:var(--text-secondary);margin-top:4px;">TSSL kỳ vọng/năm</div>';
    html += '<div style="margin-top:10px;font-size:12px;"><b>σ:</b> ' + fmtPct(data.max_sharpe.vol) + ' · <b>Sharpe:</b> ' + data.max_sharpe.sharpe.toFixed(2) + '</div>';
    html += '</div>';
  }

  // GMV
  if(data.gmv){
    html += '<div class="tcard" style="border-left:4px solid var(--primary-light);">';
    html += '<div style="font-size:11px;color:var(--text-muted);font-weight:700;margin-bottom:6px;">🛡️ GMV (RỦI RO TỐI THIỂU)</div>';
    html += '<div style="font-size:24px;font-weight:700;font-family:var(--font-mono);">' + fmtPct(data.gmv.vol) + '</div>';
    html += '<div style="font-size:12px;color:var(--text-secondary);margin-top:4px;">Độ lệch chuẩn</div>';
    html += '<div style="margin-top:10px;font-size:12px;"><b>E(R):</b> ' + fmtPct(data.gmv.ret) + ' · <b>Sharpe:</b> ' + data.gmv.sharpe.toFixed(2) + '</div>';
    html += '</div>';
  }

  html += '</div>';

  // Bang ty trong toi uu
  html += '<div class="tcard" style="margin-bottom:20px;">';
  html += '<h3 style="color:var(--primary);margin-bottom:14px;font-size:14px;font-weight:700;">📋 Tỷ Trọng Đề Xuất</h3>';
  html += '<table style="width:100%;font-size:13px;border-collapse:collapse;">';
  html += '<thead><tr style="background:var(--bg-soft);">'
    + '<th style="text-align:left;padding:10px;border-bottom:1px solid var(--border);">Mã</th>'
    + '<th style="text-align:right;padding:10px;border-bottom:1px solid var(--border);">Hiện tại</th>'
    + '<th style="text-align:right;padding:10px;border-bottom:1px solid var(--border);">Max Sharpe</th>'
    + '<th style="text-align:right;padding:10px;border-bottom:1px solid var(--border);">GMV</th>'
    + '<th style="text-align:center;padding:10px;border-bottom:1px solid var(--border);">Chênh lệch (MS)</th>'
    + '</tr></thead><tbody>';

  data.symbols.forEach(function(sym, i){
    var cur = data.user_weights[i] * 100;
    var ms = data.max_sharpe_weights ? data.max_sharpe_weights[i] * 100 : null;
    var gmv = data.gmv_weights ? data.gmv_weights[i] * 100 : null;
    var diff = (ms != null) ? (ms - cur) : null;
    var diffStr = '—';
    var diffColor = 'var(--text-muted)';
    if(diff != null){
      if(diff > 1){ diffStr = '↑ +' + diff.toFixed(1) + '%'; diffColor = 'var(--green)'; }
      else if(diff < -1){ diffStr = '↓ ' + diff.toFixed(1) + '%'; diffColor = 'var(--red)'; }
      else { diffStr = '≈ ' + diff.toFixed(1) + '%'; }
    }
    html += '<tr>'
      + '<td style="padding:10px;border-bottom:1px solid var(--border);font-weight:700;font-family:var(--font-mono);">' + sym + '</td>'
      + '<td style="padding:10px;border-bottom:1px solid var(--border);text-align:right;font-family:var(--font-mono);">' + cur.toFixed(1) + '%</td>'
      + '<td style="padding:10px;border-bottom:1px solid var(--border);text-align:right;font-family:var(--font-mono);">' + (ms != null ? ms.toFixed(1) + '%' : '—') + '</td>'
      + '<td style="padding:10px;border-bottom:1px solid var(--border);text-align:right;font-family:var(--font-mono);">' + (gmv != null ? gmv.toFixed(1) + '%' : '—') + '</td>'
      + '<td style="padding:10px;border-bottom:1px solid var(--border);text-align:center;font-weight:700;color:' + diffColor + ';font-size:12px;">' + diffStr + '</td>'
      + '</tr>';
  });

  html += '</tbody></table>';
  html += '</div>';

  // Chi so danh muc
  html += '<div class="tcard" style="margin-bottom:20px;">';
  html += '<h3 style="color:var(--primary);margin-bottom:14px;font-size:14px;font-weight:700;">📈 Chỉ Số Danh Mục</h3>';
  html += '<div class="m-grid">';
  html += '<div class="m-item"><div class="m-lb">Beta danh mục</div><div class="m-vl">' + (data.beta_portfolio != null ? data.beta_portfolio : '—') + '</div></div>';
  html += '<div class="m-item"><div class="m-lb">Chỉ số đa dạng hóa (DR)</div><div class="m-vl">' + (data.diversification_ratio || '—') + '</div></div>';
  html += '<div class="m-item"><div class="m-lb">Số phiên dữ liệu</div><div class="m-vl">' + (data.days || 0) + '</div></div>';
  html += '<div class="m-item"><div class="m-lb">Lãi suất phi rủi ro</div><div class="m-vl">' + ((data.rf_rate || 0.033) * 100).toFixed(1) + '%</div></div>';
  html += '</div>';
  html += '</div>';

  // Chart
  if(data.chart){
    html += '<div class="tcard" style="margin-bottom:20px;">';
    html += '<h3 style="color:var(--primary);margin-bottom:14px;font-size:14px;font-weight:700;">🎯 Đường Biên Hiệu Quả</h3>';
    html += '<div style="text-align:center;"><img src="data:image/png;base64,' + data.chart + '" style="max-width:100%;border-radius:8px;"></div>';
    html += '</div>';
  }

  // Correlation matrix
  if(data.correlation_matrix){
    html += '<div class="tcard" style="margin-bottom:20px;">';
    html += '<h3 style="color:var(--primary);margin-bottom:14px;font-size:14px;font-weight:700;">🔗 Ma Trận Tương Quan</h3>';
    var syms = Object.keys(data.correlation_matrix);
    html += '<table style="width:100%;font-size:12px;border-collapse:collapse;">';
    html += '<thead><tr><th style="padding:8px;border:1px solid var(--border);background:var(--bg-soft);"></th>';
    syms.forEach(function(s){ html += '<th style="padding:8px;border:1px solid var(--border);background:var(--bg-soft);font-family:var(--font-mono);">' + s + '</th>'; });
    html += '</tr></thead><tbody>';
    syms.forEach(function(s1){
      html += '<tr><td style="padding:8px;border:1px solid var(--border);font-weight:700;background:var(--bg-soft);font-family:var(--font-mono);">' + s1 + '</td>';
      syms.forEach(function(s2){
        var v = data.correlation_matrix[s1][s2];
        var color = 'var(--text-secondary)';
        var bg = 'transparent';
        if(v >= 0.7){ color = '#fff'; bg = '#EF4444'; }
        else if(v >= 0.4){ color = '#fff'; bg = '#F59E0B'; }
        else if(v <= -0.2){ color = '#fff'; bg = '#10B981'; }
        else { bg = 'var(--bg-soft)'; }
        html += '<td style="padding:8px;border:1px solid var(--border);text-align:center;font-family:var(--font-mono);color:' + color + ';background:' + bg + ';">' + v.toFixed(2) + '</td>';
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    html += '<div style="margin-top:10px;font-size:11px;color:var(--text-muted);">🟥 cao (≥0.7) · 🟧 trung bình (≥0.4) · ⬜ thấp · 🟩 âm (đa dạng hóa tốt)</div>';
    html += '</div>';
  }

  // Ghi chu
  html += '<div class="tcard" style="background:var(--amber-bg);border-color:var(--amber-border);">';
  html += '<div style="font-size:12px;color:var(--text-secondary);">';
  html += '⚠️ <b>Lưu ý:</b> Kết quả tối ưu Markowitz dựa trên dữ liệu quá khứ 2 năm, có sai số lớn. Đây là <b>công cụ tham khảo</b>, không phải khuyến nghị đầu tư. Hiệu suất quá khứ không đảm bảo cho tương lai.';
  html += '</div></div>';

  el.innerHTML = html;
}

function init(){
  document.getElementById('sTotal').textContent=STOCK_DATA.length;
  document.getElementById('sUp').textContent=STOCK_DATA.filter(s=>s.pct>0).length;
  document.getElementById('sDown').textContent=STOCK_DATA.filter(s=>s.pct<0).length;
  document.getElementById('sRef').textContent=STOCK_DATA.filter(s=>s.pct===0).length;
  document.getElementById('fTotal').textContent=STOCK_DATA.length;
  document.getElementById('lastUpdate').textContent=UPDATE_TIME;
  document.getElementById('search').addEventListener('input',()=>{currentPage=1;renderTable();});
  updateClock();
  setInterval(updateClock,1000);
  renderTable();
  initChatAI();
  loadWatchlist();
  initCompare();
}
init();
</script>

<!-- PROGRESS MODAL -->
<div class="modal-ov" id="progressModal">
  <div class="modal" style="max-width:500px;">
    <div style="text-align:center;padding:20px 0;">
      <div style="font-size:48px;margin-bottom:16px;" id="progressIcon">⚡</div>
      <div style="font-size:18px;font-weight:700;color:var(--primary);margin-bottom:8px;">Đang cập nhật toàn bộ</div>
      <div id="progressStep" style="color:var(--text-secondary);font-size:13px;margin-bottom:20px;">Đang khởi động...</div>
      <div style="background:var(--bg-soft);height:12px;border-radius:6px;overflow:hidden;margin-bottom:12px;">
        <div id="progressBar" style="height:100%;width:0%;background:linear-gradient(90deg,var(--primary),var(--primary-light));transition:width .5s;border-radius:6px;"></div>
      </div>
      <div id="progressPercent" style="font-size:24px;font-weight:700;color:var(--primary);font-family:var(--font-mono);">0%</div>
      <div style="margin-top:16px;font-size:12px;color:var(--text-muted);">Quá trình mất ~5 phút. Bạn có thể đóng và chờ.</div>
      <button onclick="closeProgressModal()" style="margin-top:20px;padding:8px 20px;background:var(--bg-soft);color:var(--text-secondary);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:12px;">Đóng (chạy ngầm)</button>
    </div>
  </div>
</div>

</body>
</html>
"""


# ============================================================
# PROGRESS TRACKING
# ============================================================
WORKFLOW_PROGRESS = {
    'is_running': False,
    'step': '',
    'percent': 0,
    'started_at': None,
    'finished_at': None,
    'error': None,
    'duration': None,
}


def _set_progress(step, percent):
    WORKFLOW_PROGRESS['step'] = step
    WORKFLOW_PROGRESS['percent'] = percent
    print(f"  [PROGRESS] {percent}% - {step}")


def create_html(df, valuations, industries, industry_roe, ai_market, ssi_reports, technical, rss_news, groups):
    if df.empty:
        return
    records = []
    for _, row in df.iterrows():
        records.append({
            'symbol': str(row.get('symbol', '')),
            'exchange': str(row.get('exchange', '')),
            'ceiling': float(row['ceiling']) if pd.notna(row.get('ceiling')) else None,
            'floor': float(row['floor']) if pd.notna(row.get('floor')) else None,
            'reference': float(row['reference']) if pd.notna(row.get('reference')) else None,
            'close': float(row['close']) if pd.notna(row.get('close')) else None,
            'open': float(row['open']) if pd.notna(row.get('open')) else None,
            'high': float(row['high']) if pd.notna(row.get('high')) else None,
            'low': float(row['low']) if pd.notna(row.get('low')) else None,
            'volume': int(row['volume']) if pd.notna(row.get('volume')) else 0,
            'change': float(row['change']) if pd.notna(row.get('change')) else 0,
            'pct': float(row['pct']) if pd.notna(row.get('pct')) else 0,
            'foreign_buy': int(row['foreign_buy']) if pd.notna(row.get('foreign_buy')) else 0,
            'foreign_sell': int(row['foreign_sell']) if pd.notna(row.get('foreign_sell')) else 0,
            'foreign_net': int(row['foreign_net']) if pd.notna(row.get('foreign_net')) else 0,
            'bid_price_1': float(row['bid_price_1']) if pd.notna(row.get('bid_price_1')) else None,
            'bid_vol_1': int(row['bid_vol_1']) if pd.notna(row.get('bid_vol_1')) else 0,
            'bid_price_2': float(row['bid_price_2']) if pd.notna(row.get('bid_price_2')) else None,
            'bid_vol_2': int(row['bid_vol_2']) if pd.notna(row.get('bid_vol_2')) else 0,
            'bid_price_3': float(row['bid_price_3']) if pd.notna(row.get('bid_price_3')) else None,
            'bid_vol_3': int(row['bid_vol_3']) if pd.notna(row.get('bid_vol_3')) else 0,
            'ask_price_1': float(row['ask_price_1']) if pd.notna(row.get('ask_price_1')) else None,
            'ask_vol_1': int(row['ask_vol_1']) if pd.notna(row.get('ask_vol_1')) else 0,
            'ask_price_2': float(row['ask_price_2']) if pd.notna(row.get('ask_price_2')) else None,
            'ask_vol_2': int(row['ask_vol_2']) if pd.notna(row.get('ask_vol_2')) else 0,
            'ask_price_3': float(row['ask_price_3']) if pd.notna(row.get('ask_price_3')) else None,
            'ask_vol_3': int(row['ask_vol_3']) if pd.notna(row.get('ask_vol_3')) else 0,
            'time': str(row['time'])[:19] if pd.notna(row.get('time')) else None,
        })

    time_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    html = (HTML_TEMPLATE
            .replace('__DATA__', json.dumps(records, ensure_ascii=False))
            .replace('__VALUATION__', json.dumps(valuations, ensure_ascii=False))
            .replace('__SCORING__', json.dumps(scores if 'scores' in dir() else {}, ensure_ascii=False))
            .replace('__INDUSTRY__', json.dumps(industries, ensure_ascii=False))
            .replace('__INDUSTRY_ROE__', json.dumps(industry_roe, ensure_ascii=False))
            .replace('__TECHNICAL__', json.dumps(technical, ensure_ascii=False))
            .replace('__RSS_NEWS__', json.dumps(rss_news, ensure_ascii=False))
            .replace('__GROUPS__', json.dumps(groups, ensure_ascii=False))
            .replace('__TIME__', time_str))
    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  -> Da tao {HTML_FILE} ({len(records)} ma)")


def run_workflow():
    global WORKFLOW_PROGRESS
    WORKFLOW_PROGRESS['is_running'] = True
    WORKFLOW_PROGRESS['started_at'] = datetime.now().strftime('%H:%M:%S')
    WORKFLOW_PROGRESS['error'] = None
    WORKFLOW_PROGRESS['percent'] = 0

    _start = time.time()
    try:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] === BAT DAU ===")

        _set_progress('Đang lấy danh sách mã...', 3)
        df = fetch_all_data()
        if df.empty:
            print("  -> Khong co du lieu.")
            WORKFLOW_PROGRESS['error'] = 'Khong co du lieu'
            return
        df.to_excel(EXCEL_FILE, index=False)
        print(f"  -> Da luu {EXCEL_FILE} ({len(df)} dong)")
        _set_progress('Đã lấy danh sách mã', 15)

        _set_progress('Đang lấy chỉ số định giá...', 20)
        try:
            df_sorted = df.sort_values('volume', ascending=False).head(VALUATION_LIMIT)
            price_map = {}
            for _, row in df_sorted.iterrows():
                sym = str(row['symbol'])
                close = float(row['close']) if pd.notna(row.get('close')) else None
                price_map[sym] = close
            valuations = fetch_all_valuations(price_map)
            print(f"  -> Da lay {len(valuations)} ma")
        except Exception as e:
            print(f"  [Loi Valuation] {e}")
            valuations = {}
        _set_progress('Đã xong định giá', 35)

        _set_progress('Đang phân loại ngành...', 40)
        try:
            df_sorted2 = df.sort_values('volume', ascending=False).head(VALUATION_LIMIT)
            top_syms2 = [str(row['symbol']) for _, row in df_sorted2.iterrows()]
            industries = fetch_all_industries(top_syms2)
        except Exception as e:
            print(f"  [Loi Industry] {e}")
            industries = {}
        industry_roe = compute_industry_roe(valuations, industries)
        print(f"  [ROE] Da tinh ROE cho {len(industry_roe)} nganh")
        _set_progress('Đã phân loại ngành', 45)

        _set_progress('Đang tính MA, RSI...', 50)
        try:
            df_top = df.sort_values('volume', ascending=False).head(20)
            ta_symbols = [str(row['symbol']) for _, row in df_top.iterrows()]
            technical = fetch_all_technical(ta_symbols)
        except Exception as e:
            print(f"  [Loi TA] {e}")
            technical = {}
        _set_progress('Đã tính xong kỹ thuật', 55)

        _set_progress('Đang gọi AI viết nhận định...', 60)
        try:
            top_up = sorted([{'symbol': r['symbol'], 'pct': r['pct']} for _, r in df.iterrows() if r['pct'] > 0],
                            key=lambda x: x['pct'], reverse=True)[:5]
            top_down = sorted([{'symbol': r['symbol'], 'pct': r['pct']} for _, r in df.iterrows() if r['pct'] < 0],
                              key=lambda x: x['pct'])[:5]
            ai_market = generate_market_overview(top_up, top_down, valuations)
            if ai_market.get('report'):
                print(f"  -> AI OK ({len(ai_market['report'])} ky tu)")
        except Exception as e:
            print(f"  [Loi AI] {e}")
            ai_market = {'error': str(e), 'report': None}
        _set_progress('AI đã viết xong', 68)

        _set_progress('Đang lấy nhóm chỉ số...', 70)
        try:
            groups = fetch_symbol_groups()
        except Exception as e:
            print(f"  [Loi Group] {e}")
            groups = {}
        _set_progress('Đã lấy xong nhóm', 72)

        _set_progress('Đang lấy tin tức RSS...', 75)
        try:
            rss_news = fetch_all_news(max_per_feed=8)
            print(f"  -> Da lay {len(rss_news)} tin")
        except Exception as e:
            print(f"  [Loi RSS] {e}")
            rss_news = []
        _set_progress('Đã lấy xong tin tức', 78)

        _set_progress('Đang scrape báo cáo 16 CTCK (chậm nhất)...', 80)
        try:
            try:
                from hf_compat import should_skip_playwright
                if should_skip_playwright():
                    print("  [Reports] HF mode - bo qua scrape CTCK")
                    ssi_reports = []
                else:
                    ssi_reports = fetch_ssi_reports()
            except ImportError:
                ssi_reports = fetch_ssi_reports()
            print(f"  -> Da lay {len(ssi_reports)} bao cao")
        except Exception as e:
            print(f"  [Loi Reports] {e}")
            ssi_reports = []
        _set_progress('Đã scrape xong báo cáo', 92)

        _set_progress('Đang tạo file PDF...', 94)
        try:
            records_for_pdf = [
                {
                    'symbol': str(r['symbol']),
                    'close': float(r['close']) if pd.notna(r.get('close')) else 0,
                    'pct': float(r['pct']) if pd.notna(r.get('pct')) else 0,
                    'volume': int(r['volume']) if pd.notna(r.get('volume')) else 0,
                }
                for _, r in df.iterrows()
            ]
            pdf_files = generate_all_reports(
                records_for_pdf,
                ai_report=ai_market.get('report') if ai_market else None
            )
            if pdf_files:
                print(f"  -> Da tao {len(pdf_files)} file PDF")
        except Exception as e:
            print(f"  [Loi PDF] {e}")
        _set_progress('Đã tạo xong PDF', 97)

        # Phan tich khuyen nghi CTCK

        try:
            from ctck_analyzer import analyze_reports as _ctck_analyze
            ctck_data = _ctck_analyze(ssi_reports)
            from ctck_analyzer import save_cache as _ctck_save
            _ctck_save(ctck_data)
            print(f"  [CTCK] Da trich xuat khuyen nghi cho {len(ctck_data)} ma")
        except Exception as e:
            print(f"  [CTCK] Loi: {e}")

        caches = {
              'valuations': valuations,
	}
        # Cham diem tong hop
        try:
            from scoring import compute_all_scores, save_cache as score_save
            stock_map = {str(r['symbol']): {'close': float(r['close']) if pd.notna(r.get('close')) else 0,
                                            'pct': float(r['pct']) if pd.notna(r.get('pct')) else 0}
                         for _, r in df.iterrows()}
            scores = compute_all_scores(
                stock_map, valuations, technical, industries,
                industry_roe, ctck_data, rss_news
            )
            score_save(scores)
            print(f"  [Scoring] Da cham diem {len(scores)} ma")
            caches['scores'] = scores
        except Exception as e:
            print(f"  [Scoring] Loi: {e}")
            scores = {}

        # Tinh chi so rui ro
        try:
            from risk_metrics import compute_all_risk, save_cache as risk_save
            top_risk_syms = [str(r['symbol']) for _, r in df.sort_values('volume', ascending=False).head(30).iterrows()]
            risk_data = compute_all_risk(top_risk_syms)
            risk_save(risk_data)
            print(f"  [Risk] Da tinh rui ro cho {len(risk_data)} ma")
            caches['risk'] = risk_data
        except Exception as e:
            print(f"  [Risk] Loi: {e}")
            risk_data = {}

        try:
            caches = {
                'valuations': valuations,
                'industries': industries,
                'industry_roe': industry_roe,
                'ai_market': ai_market,
                'ssi_reports': ssi_reports,
                'technical': technical,
                'rss_news': rss_news,
                'groups': groups,
                'risk': risk_data,
                'scores': scores,
                'ctck_data': ctck_data,
            }
            with open('dashboard_caches.json', 'w', encoding='utf-8') as f:
                json.dump(caches, f, ensure_ascii=False)
        except Exception as e:
            print(f"  [Cache] Loi: {e}")

        _set_progress('Đang tạo HTML...', 98)
        create_html(df, valuations, industries, industry_roe, ai_market, ssi_reports, technical, rss_news, groups)

        _set_progress('HOÀN TẤT', 100)
        _elapsed = time.time() - _start
        WORKFLOW_PROGRESS['duration'] = round(_elapsed, 1)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] === XONG. Mat {_elapsed:.0f}s ===")

    except Exception as e:
        import traceback
        traceback.print_exc()
        WORKFLOW_PROGRESS['error'] = str(e)[:200]
    finally:
        WORKFLOW_PROGRESS['is_running'] = False
        WORKFLOW_PROGRESS['finished_at'] = datetime.now().strftime('%H:%M:%S')


if __name__ == "__main__":
    print("=" * 60)
    print("  DASHBOARD CO PHIEU VIET NAM - 10 TABS")
    print("=" * 60)
    print(f"  API Key: {VNSTOCK_API_KEY[:20]}...")
    print(f"  VALUATION_LIMIT: {VALUATION_LIMIT} ma")
    print("=" * 60)
    run_workflow()
    schedule.every(UPDATE_INTERVAL_MINUTES).minutes.do(run_workflow)
    while True:
        schedule.run_pending()
        time.sleep(1)