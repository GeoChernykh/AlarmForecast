"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { ComposableMap, Geographies, Geography } from 'react-simple-maps';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield, ShieldAlert, Clock, Activity, X, Map as MapIcon,
  RefreshCw, BarChart2, TrendingUp, AlertTriangle, Info
} from 'lucide-react';

const GEO_URL = "/Ukraine-regions.json";

// ─── Region mapping: region_id (CSV) → GeoJSON NAME_1 ────────────────────────
const REGION_MAP = {
  3:  "Хмельницька область",
  4:  "Вінницька область",
  5:  "Рівненська область",
  8:  "Волинська область",
  9:  "Дніпропетровська область",
  10: "Житомирська область",
  11: "Закарпатська область",
  12: "Запорізька область",
  13: "Івано-Франківська область",
  14: "Київська область",
  15: "Кіровоградська область",
  16: "Луганська область",
  17: "Миколаївська область",
  18: "Одеська область",
  19: "Полтавська область",
  20: "Сумська область",
  21: "Тернопільська область",
  22: "Харківська область",
  23: "Херсонська область",
  24: "Черкаська область",
  25: "Чернігівська область",
  26: "Чернівецька область",
  27: "Львівська область",
  28: "Донецька область",
  31: "Київ",
};

const ALWAYS_RED_REGIONS = [
  "Луганська область",
  "Автономна Республіка Крим",
  "Севастополь"
];

const VALID_REGIONS = new Set([...Object.values(REGION_MAP), ...ALWAYS_RED_REGIONS]);

// ─── 24 time slots starting from current hour ──────────────────────────

const buildTimeSlots = (baseDate) => {
  return Array.from({ length: 24 }, (_, i) => {
    const t = new Date(baseDate.getTime() + i * 60 * 60 * 1000);
    return {
      label: `${String(t.getHours()).padStart(2, '0')}:00`,
      date: t,
      offset: i,
    };
  });
};

// ─── Color helpers ────────────────────────────────────────────────────────────
const probToFill = (p) => {
  if (p == null) return '#0f172a';
  if (p < 0.15)  return '#1e293b';
  if (p < 0.35)  return '#1c3a1e';
  if (p < 0.55)  return '#78350f';
  if (p < 0.75)  return '#7c2d12';
  return '#7f1d1d';
};
const probToStroke = (p, selected) => {
  if (selected) return '#60a5fa';
  if (p == null) return '#1e293b';
  if (p < 0.15)  return '#334155';
  if (p < 0.35)  return '#16a34a';
  if (p < 0.55)  return '#d97706';
  if (p < 0.75)  return '#ea580c';
  return '#ef4444';
};
const probToHoverFill = (p) => {
  if (p == null || p < 0.15) return '#334155';
  if (p < 0.35) return '#14532d';
  if (p < 0.55) return '#92400e';
  if (p < 0.75) return '#9a3412';
  return '#991b1b';
};
const probToLabel = (p) => {
  if (p == null) return { text: 'Немає даних', cls: 'text-slate-500', bg: 'bg-slate-700/20 border-slate-600/20', Icon: Shield };
  if (p < 0.15)  return { text: 'Безпечно',   cls: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20', Icon: Shield };
  if (p < 0.35)  return { text: 'Низька',     cls: 'text-green-400',   bg: 'bg-green-500/10   border-green-500/20',   Icon: Shield };
  if (p < 0.55)  return { text: 'Середня',    cls: 'text-amber-400',   bg: 'bg-amber-500/10   border-amber-500/20',   Icon: ShieldAlert };
  if (p < 0.75)  return { text: 'Висока',     cls: 'text-orange-400',  bg: 'bg-orange-500/10  border-orange-500/20',  Icon: ShieldAlert };
  return           { text: 'Критична',   cls: 'text-rose-400',    bg: 'bg-rose-500/10    border-rose-500/20',    Icon: ShieldAlert };
};
const probToBarColor = (p) => {
  if (p == null || p < 0.15) return '#334155';
  if (p < 0.35) return '#16a34a';
  if (p < 0.55) return '#d97706';
  if (p < 0.75) return '#ea580c';
  return '#ef4444';
};

const LEGEND_ITEMS = [
  { label: 'Безпечно', range: '0–15%',   fill: '#1e293b', stroke: '#334155' },
  { label: 'Низька',   range: '15–35%',  fill: '#1c3a1e', stroke: '#16a34a' },
  { label: 'Середня',  range: '35–55%',  fill: '#78350f', stroke: '#d97706' },
  { label: 'Висока',   range: '55–75%',  fill: '#7c2d12', stroke: '#ea580c' },
  { label: 'Критична', range: '75–100%', fill: '#7f1d1d', stroke: '#ef4444' },
];

// ─── Mock data: generates for exactly 24 hours from baseDate ─────────────────
const generateMockPredictions = (baseDate) => {
  const slots = buildTimeSlots(baseDate);
  const HIGH = new Set([16, 22, 12, 28, 23]);
  const MED  = new Set([9, 17, 20, 25]);

  return Object.fromEntries(
    Object.entries(REGION_MAP).map(([idStr, name]) => {
      const id   = Number(idStr);
      const base = HIGH.has(id) ? 0.72 : MED.has(id) ? 0.38 : 0.12;
      const hours = {};
      slots.forEach(({ label }) => {
        const noise = (Math.random() - 0.5) * 0.3;
        hours[label] = parseFloat(Math.max(0, Math.min(1, base + noise)).toFixed(2));
      });
      return [name, hours];
    })
  );
};

/**
 * ════════════════════════════════════════════════════════════════
 *  ФОРМАТ JSON від API (варіант по region_id):
 * ════════════════════════════════════════════════════════════════
 *
 * {
 *   "generated_at": "2025-04-11T16:00:00Z",
 *   "predictions_by_id": {
 *     "3":  { "16:00": 0.10, "17:00": 0.08, ..., "15:00": 0.12 },
 *     "22": { "16:00": 0.87, "17:00": 0.91, ..., "15:00": 0.74 },
 *     ...
 *   }
 * }
 *
 * Ключі у predictions_by_id — це region_id з таблиці regions.csv.
 * Ключі в об'єкті регіону — години прогнозу у форматі "HH:00",
 *   рівно 24 значення починаючи з поточної години.
 * Значення — float 0.0–1.0 (ймовірність тривоги).
 */
const fetchPredictions = async (url, slots) => {
  const res = await fetch(url, {
    cache: 'no-store',
    headers: {
      'X-API-Key': process.env.ALARM_FORECAST_API_KEY
    }
  });

  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = await res.json();

  const raw = json.regions_forecast ?? json;
  const normalizeProb = (p) => (p > 1 ? p / 100 : p);
  const converted = {};

  for (const [apiName, hours] of Object.entries(raw)) {
    const regionName = apiName.replace(" обл.", " область");
    if (regionName) {
      converted[regionName] = {};
      for (const [timeStr, prob] of Object.entries(hours)) {
        converted[regionName][timeStr] = normalizeProb(prob);
      }
    }
  }

  ALWAYS_RED_REGIONS.forEach(region => {
    converted[region] = {};
    slots.forEach(slot => {
      converted[region][slot.label] = 1.0;
    });
  });

  return converted;
};

// ─── Sparkline SVG component ──────────────────────────────────────────────────
const ProbabilityChart = ({ data, slots, currentOffset }) => {
  const W = 280, H = 64, PAD = 4;
  const values = slots.map(s => data?.[s.label] ?? 0);
  const points = values.map((v, i) => {
    const x = PAD + (i / 23) * (W - PAD * 2);
    const y = PAD + (1 - v) * (H - PAD * 2);
    return [x, y];
  });

  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const areaD = pathD + ` L${points[points.length-1][0].toFixed(1)},${H} L${points[0][0].toFixed(1)},${H} Z`;

  const curX = PAD + (currentOffset / 23) * (W - PAD * 2);
  const curY = points[currentOffset]?.[1] ?? H / 2;
  const curProb = values[currentOffset];

  // 0.5 threshold line Y
  const threshY = PAD + 0.5 * (H - PAD * 2);

  return (
    <div className="px-1 pt-1 pb-2">
      <div className="flex justify-between text-[9px] font-mono text-slate-500 mb-1 px-1">
        <span>{slots[0]?.label}</span>
        <span className="text-slate-400">Динаміка ймовірності</span>
        <span>{slots[23]?.label}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 64 }}>
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ef4444" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#ef4444" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* 50% threshold line */}
        <line x1={PAD} y1={threshY} x2={W - PAD} y2={threshY} stroke="#475569" strokeWidth="0.5" strokeDasharray="3,3" />
        <text x={W - PAD - 2} y={threshY - 2} fill="#475569" fontSize="6" textAnchor="end">50%</text>

        {/* Area fill */}
        <path d={areaD} fill="url(#areaGrad)" />

        {/* Line */}
        <path d={pathD} fill="none" stroke="#f43f5e" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />

        {/* Current time vertical */}
        <line x1={curX} y1={PAD} x2={curX} y2={H} stroke="#60a5fa" strokeWidth="1" strokeDasharray="2,2" />

        {/* Current dot */}
        <circle cx={curX} cy={curY} r="3" fill="#60a5fa" stroke="#050B14" strokeWidth="1.5" />

        {/* Tooltip bubble */}
        <rect
          x={Math.min(curX - 14, W - 32)} y={curY - 16}
          width="28" height="12" rx="3"
          fill="#1e293b" stroke="#334155" strokeWidth="0.5"
        />
        <text
          x={Math.min(curX, W - 18)} y={curY - 7}
          fill="#e2e8f0" fontSize="7" textAnchor="middle" fontFamily="monospace"
        >
          {Math.round(curProb * 100)}%
        </text>
      </svg>
      <div className="flex justify-between text-[9px] font-mono text-slate-600 px-1 mt-0.5">
        <span>0%</span>
        <span>50% поріг тривоги</span>
        <span>100%</span>
      </div>
    </div>
  );
};

// ─── Main Component ───────────────────────────────────────────────────────────
export default function TacticalDashboard() {
  const [currentTime, setCurrentTime] = useState(null);   // snapped to current hour
  const [predictionData, setPredictionData] = useState({});
  const [selectedHourOffset, setSelectedHourOffset] = useState(0); // 0–23 from currentTime
  const [selectedRegionName, setSelectedRegionName] = useState(null);

  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showStats, setShowStats] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  useEffect(() => {
    const now = new Date();
    now.setMinutes(0, 0, 0);
    setCurrentTime(now);
  }, []);

  // 24 slots from current hour
  const timeSlots = useMemo(() => currentTime ? buildTimeSlots(currentTime) : [], [currentTime]);

  const loadData = useCallback(async () => {
    if (!currentTime) return;
    setIsRefreshing(true);

    try {
      // call Flask api
      const realData = await fetchPredictions("http://100.54.113.147:8000/forecast", timeSlots);
      setPredictionData(realData);
    } catch (error) {
      console.error("Не вдалося отримати дані з API. Вмикаю демо-режим.", error);
      // if flask is down turn on demo
      setPredictionData(generateMockPredictions(currentTime));
    } finally {
      setIsRefreshing(false);
    }
  }, [currentTime, timeSlots]);

  useEffect(() => {
    if (currentTime) loadData();
  }, [currentTime, loadData]);

  const selectedSlot = timeSlots[selectedHourOffset];
  const selectedTimeStr = selectedSlot?.label ?? '00:00';

  // How many regions are above 0.5 threshold at selected time
  const alarmsCount = useMemo(() =>
    Object.values(predictionData).filter(r => (r?.[selectedTimeStr] ?? 0) >= 0.5).length,
    [predictionData, selectedTimeStr]
  );

  const stats = useMemo(() => {
    if (!Object.keys(predictionData).length || !timeSlots.length) return null;
    const regions = Object.values(predictionData);
    const total = regions.length;

    const getP = (r) => r?.[selectedTimeStr] ?? 0;
    const critical = regions.filter(r => getP(r) >= 0.75).length;
    const high     = regions.filter(r => getP(r) >= 0.55 && getP(r) < 0.75).length;
    const medium   = regions.filter(r => getP(r) >= 0.35 && getP(r) < 0.55).length;
    const safe     = regions.filter(r => getP(r) < 0.35).length;
    const avgProb  = regions.reduce((s, r) => s + getP(r), 0) / total;

    const trend = timeSlots.map(s => {
      const avg = regions.reduce((sum, r) => sum + (r?.[s.label] ?? 0), 0) / total;
      return avg;
    });

    const topDanger = Object.entries(predictionData)
      .filter(([name]) => !ALWAYS_RED_REGIONS.includes(name)) // <-- Додано фільтр
      .map(([name, hours]) => ({
        name,
        avgProb: timeSlots.reduce((s, sl) => s + (hours?.[sl.label] ?? 0), 0) / timeSlots.length,
      }))
      .sort((a, b) => b.avgProb - a.avgProb)
      .slice(0, 3);

    return { critical, high, medium, safe, total, avgProb, trend, topDanger };
  }, [predictionData, selectedTimeStr, timeSlots]);

  const selectedRegionData = selectedRegionName ? predictionData[selectedRegionName] : null;
  const selectedRegionAvg = useMemo(() => {
    if (!selectedRegionData || !timeSlots.length) return 0;
    return timeSlots.reduce((s, sl) => s + (selectedRegionData[sl.label] ?? 0), 0) / timeSlots.length;
  }, [selectedRegionData, timeSlots]);

  if (!currentTime || !Object.keys(predictionData).length) {
    return (
      <div className="bg-[#050B14] text-emerald-500 min-h-screen flex flex-col items-center justify-center font-mono gap-3">
        <Activity size={32} className="animate-pulse" />
        <span className="text-sm tracking-widest uppercase">Ініціалізація системи...</span>
      </div>
    );
  }

  // ── Region sidebar/sheet panel ─────────────────────────────────────────────
  const PanelContent = () => {
    const lbl = probToLabel(selectedRegionAvg);
    return (
      <>
        {/* Header */}
        <div className="p-4 md:p-5 bg-slate-800/30 border-b border-slate-700/50 flex justify-between items-start shrink-0 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/10 blur-3xl rounded-full -mr-10 -mt-10 pointer-events-none" />
          <div className="relative z-10 min-w-0 pr-2">
            <h3 className="text-base md:text-xl font-bold text-white leading-tight truncate">{selectedRegionName}</h3>
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              <span className="text-[10px] text-blue-400 font-mono bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20 flex items-center gap-1">
                <MapIcon size={9} /> Прогноз 24 год
              </span>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border flex items-center gap-1 ${lbl.cls} ${lbl.bg}`}>
                Середнє: {Math.round(selectedRegionAvg * 100)}%
              </span>
            </div>
          </div>
          <button
            onClick={() => setSelectedRegionName(null)}
            className="text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-700 p-2 rounded-full transition-colors border border-slate-600/50 shrink-0 relative z-10"
          >
            <X size={16} />
          </button>
        </div>

        {/* Probability chart */}
        {selectedRegionData && (
          <div className="shrink-0 border-b border-slate-700/50 bg-slate-800/20 px-3 pt-3 pb-1">
            <ProbabilityChart
              data={selectedRegionData}
              slots={timeSlots}
              currentOffset={selectedHourOffset}
            />
          </div>
        )}

        {/* Hourly list */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1 custom-scrollbar">
          {timeSlots.map((slot, idx) => {
            const prob   = selectedRegionData?.[slot.label] ?? null;
            const isCur  = idx === selectedHourOffset;
            const hl     = probToLabel(prob);
            const Icon   = hl.Icon;
            return (
              <button
                key={slot.label}
                onClick={() => setSelectedHourOffset(idx)}
                className={`w-full flex items-center justify-between p-2.5 rounded-xl transition-all duration-150 text-left relative overflow-hidden
                  ${isCur ? 'bg-slate-800 ring-1 ring-blue-500/60 shadow-[0_0_10px_rgba(59,130,246,0.15)]' : 'hover:bg-slate-800/50 bg-slate-800/10'}`}
              >
                {/* Left color bar */}
                <div className="absolute left-0 top-0 bottom-0 w-0.5 rounded-l-xl" style={{ backgroundColor: probToStroke(prob, false) }} />
                <span className={`font-mono text-xs ml-2 w-12 shrink-0 ${isCur ? 'text-blue-300' : 'text-slate-400'}`}>{slot.label}</span>
                {/* Mini bar */}
                <div className="flex-1 mx-3 h-1 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${(prob ?? 0) * 100}%`, backgroundColor: probToBarColor(prob) }}
                  />
                </div>
                <div className={`flex items-center gap-1 ${hl.cls} ${hl.bg} border px-2 py-0.5 rounded-md text-[10px] font-bold tracking-wide shrink-0`}>
                  <Icon size={10} />
                  <span className="hidden sm:inline">{hl.text}</span>
                  <span className="font-mono ml-1">{prob != null ? Math.round(prob * 100) + '%' : '—'}</span>
                </div>
              </button>
            );
          })}
        </div>
      </>
    );
  };

  return (
    <div className="relative min-h-screen bg-[#050B14] text-slate-100 font-sans overflow-hidden flex flex-col selection:bg-rose-500/30">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-950/20 via-[#050B14] to-[#050B14] pointer-events-none" />

      {/* ── Header ── */}
      <header className="absolute top-3 md:top-6 left-3 md:left-6 right-3 md:right-6 z-20 flex justify-between items-start gap-2 pointer-events-none">
        <motion.div
          initial={{ y: -40, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
          className="bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 p-3 md:p-5 rounded-xl md:rounded-2xl shadow-xl pointer-events-auto flex items-center gap-3 md:gap-4 min-w-0"
        >
          <div className="relative flex items-center justify-center w-9 h-9 md:w-11 md:h-11 bg-rose-500/10 rounded-full border border-rose-500/30 shrink-0">
            <Activity className="text-rose-500 animate-pulse" size={isMobile ? 17 : 22} />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm md:text-lg font-bold tracking-tight text-white truncate">Система Прогнозування тривог</h1>
            <div className="flex flex-wrap items-center gap-2 mt-0.5">
              <span className="text-[10px] text-emerald-400 font-mono bg-emerald-400/10 px-2 py-0.5 rounded-md border border-emerald-400/20">Модель Активна</span>
              <span className="text-[10px] text-slate-400 font-mono hidden sm:block">Тривог (&gt;50%): {alarmsCount}</span>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ y: -40, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.1 }}
          className="flex items-start gap-2 pointer-events-auto"
        >
          {/* Selected time */}
          <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 px-3 md:px-4 py-2.5 md:py-3.5 rounded-xl md:rounded-2xl shadow-xl flex items-center gap-2">
            <Clock size={15} className="text-blue-400 shrink-0" />
            <div className="flex flex-col">
              <span className="text-[9px] text-slate-400 uppercase tracking-widest font-bold hidden md:block">Перегляд</span>
              <span className="font-mono text-sm md:text-base tracking-wider text-white font-semibold">{selectedTimeStr}</span>
            </div>
          </div>

          {/* Stats */}
          <button
            onClick={() => setShowStats(s => !s)}
            className={`bg-slate-900/50 backdrop-blur-xl border p-2.5 md:p-3 rounded-xl md:rounded-2xl shadow-xl transition-colors ${showStats ? 'border-blue-500/50 text-blue-400' : 'border-slate-700/50 text-slate-400 hover:text-white'}`}
          >
            <BarChart2 size={16} />
          </button>

          {/* Refresh */}
          <button
            onClick={loadData} disabled={isRefreshing}
            className="bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 p-2.5 md:p-3 rounded-xl md:rounded-2xl shadow-xl text-slate-400 hover:text-white transition-colors disabled:opacity-50"
          >
            <RefreshCw size={16} className={isRefreshing ? 'animate-spin' : ''} />
          </button>
        </motion.div>
      </header>

      {/* ── Stats Panel ── */}
      <AnimatePresence>
        {showStats && stats && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -8, scale: 0.97 }}
            className="absolute top-20 md:top-24 right-3 md:right-6 z-30 w-80 bg-slate-900/92 backdrop-blur-2xl border border-slate-700/50 rounded-2xl shadow-2xl p-5 flex flex-col gap-4"
          >
            {/* Explanation */}
            <div className="bg-blue-500/8 border border-blue-500/20 rounded-xl p-3 flex gap-2">
              <Info size={13} className="text-blue-400 mt-0.5 shrink-0" />
              <p className="text-[10px] text-slate-300 leading-relaxed">
                <span className="text-blue-300 font-semibold">Статус на {selectedTimeStr}</span> 
              </p>
            </div>

            {/* Current status grid */}
            <div>
              <h4 className="text-xs font-semibold text-white mb-2 flex items-center gap-2">
                <Activity size={13} className="text-blue-400" /> Статус на {selectedTimeStr}
              </h4>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: 'Критична ≥75%', val: stats.critical, cls: 'text-rose-400',    bg: 'bg-rose-500/10   border-rose-500/20' },
                  { label: 'Висока ≥55%',   val: stats.high,     cls: 'text-orange-400',  bg: 'bg-orange-500/10 border-orange-500/20' },
                  { label: 'Середня ≥35%',  val: stats.medium,   cls: 'text-amber-400',   bg: 'bg-amber-500/10  border-amber-500/20' },
                  { label: 'Безпечно <35%', val: stats.safe,     cls: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
                ].map(({ label, val, cls, bg }) => (
                  <div key={label} className={`${bg} border rounded-xl p-3`}>
                    <div className={`text-2xl font-bold font-mono ${cls}`}>{val}</div>
                    <div className={`text-[9px] uppercase tracking-wide mt-0.5 ${cls} opacity-70`}>{label}</div>
                  </div>
                ))}
              </div>
              <div className="mt-2.5 bg-slate-800/50 rounded-lg p-2.5">
                <div className="flex justify-between text-[10px] text-slate-400 mb-1.5">
                  <span>Середня ймовірність</span>
                  <span className="text-white font-bold font-mono">{Math.round(stats.avgProb * 100)}%</span>
                </div>
                <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: 'linear-gradient(90deg, #16a34a, #d97706, #ef4444)' }}
                    initial={{ width: 0 }}
                    animate={{ width: `${stats.avgProb * 100}%` }}
                    transition={{ duration: 0.7, ease: 'easeOut' }}
                  />
                </div>
              </div>
            </div>

            {/* 24h trend */}
            <div className="border-t border-slate-700/50 pt-4">
              <h4 className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-2">
                <TrendingUp size={12} className="text-emerald-400" /> Динаміка за 24 год (всі регіони)
              </h4>
              <div className="flex items-end gap-px h-10">
                {stats.trend.map((avg, i) => {
                  const isNow = i === selectedHourOffset;
                  return (
                    <div key={i} className="flex-1 flex flex-col justify-end h-full">
                      <div
                        className="w-full rounded-t-sm transition-all duration-200"
                        style={{
                          height: `${Math.max(6, avg * 100)}%`,
                          backgroundColor: isNow ? '#60a5fa' : probToBarColor(avg),
                          boxShadow: isNow ? '0 0 5px rgba(96,165,250,0.7)' : undefined,
                        }}
                      />
                    </div>
                  );
                })}
              </div>
              <div className="flex justify-between mt-1 text-[8px] font-mono text-slate-600">
                <span>{timeSlots[0]?.label}</span>
                <span>{timeSlots[11]?.label}</span>
                <span>{timeSlots[23]?.label}</span>
              </div>
            </div>

            {/* Top danger */}
            <div className="border-t border-slate-700/50 pt-4">
              <h4 className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-2">
                <AlertTriangle size={12} className="text-amber-400" /> Топ зон ризику (24 год)
              </h4>
              <div className="space-y-1.5">
                {stats.topDanger.map((region, idx) => {
                  const rl = probToLabel(region.avgProb);
                  return (
                    <button
                      key={region.name}
                      onClick={() => { setSelectedRegionName(region.name); setShowStats(false); }}
                      className="w-full flex justify-between items-center bg-slate-800/40 hover:bg-slate-800 p-2 rounded-lg transition-colors text-left"
                    >
                      <span className="text-[11px] text-slate-300 truncate pr-2">
                        <span className="text-slate-500 mr-1">{idx + 1}.</span>{region.name}
                      </span>
                      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border shrink-0 ${rl.cls} ${rl.bg}`}>
                        {Math.round(region.avgProb * 100)}%
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Map ── */}
      <main className="flex-1 flex items-center justify-center relative z-0 w-full pt-20 pb-36 md:pt-24 md:pb-36 px-2">
        <ComposableMap
          projection="geoMercator"
          projectionConfig={{ scale: isMobile ? 1600 : 2300, center: [31.5, 48.5] }}
          className="w-full max-w-6xl h-auto"
        >
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const regionName = geo.properties.NAME_1;
                const inDataset  = VALID_REGIONS.has(regionName);
                const prob       = inDataset ? (predictionData[regionName]?.[selectedTimeStr] ?? null) : null;
                const isSelected = selectedRegionName === regionName;

                return (
                  <Geography
                    key={geo.rsmKey || regionName}
                    geography={geo}
                    onClick={() => {
                      if (!inDataset) return;
                      setSelectedRegionName(regionName);
                      setShowStats(false);
                    }}
                    className="transition-all duration-300 focus:outline-none"
                    style={{
                      default: {
                        fill: probToFill(prob),
                        stroke: probToStroke(prob, isSelected),
                        strokeWidth: isSelected ? 1.5 : 0.5,
                        outline: 'none',
                        opacity: inDataset ? 1 : 0.25,
                      },
                      hover: {
                        fill: inDataset ? probToHoverFill(prob) : '#0f172a',
                        stroke: inDataset ? '#94a3b8' : '#1e293b',
                        strokeWidth: 1,
                        outline: 'none',
                        cursor: inDataset ? 'pointer' : 'default',
                      },
                      pressed: { fill: '#0f172a', outline: 'none' },
                    }}
                  />
                );
              })
            }
          </Geographies>
        </ComposableMap>
      </main>

      {/* ── Legend ── */}
      <motion.div
        initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.4 }}
        className="absolute bottom-36 md:bottom-40 left-3 md:left-6 z-20 bg-slate-900/60 backdrop-blur-xl border border-slate-700/50 rounded-xl px-3 py-3 shadow-xl"
      >
        <p className="text-[9px] font-mono uppercase tracking-widest text-slate-500 mb-2">Ймовірність</p>
        {LEGEND_ITEMS.map(({ label, range, fill, stroke }) => (
          <div key={label} className="flex items-center gap-2 mb-1 last:mb-0">
            <div className="w-3 h-3 rounded-sm shrink-0 border" style={{ backgroundColor: fill, borderColor: stroke }} />
            <span className="text-[10px] text-slate-300 font-mono w-16">{label}</span>
            <span className="text-[9px] text-slate-500 font-mono">{range}</span>
          </div>
        ))}
      </motion.div>

      {/* ── Desktop Sidebar ── */}
      {!isMobile && (
        <AnimatePresence>
          {selectedRegionName && (
            <motion.aside
              initial={{ x: 380, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 380, opacity: 0 }}
              transition={{ type: 'spring', damping: 26, stiffness: 210 }}
              className="absolute right-6 top-28 bottom-36 w-[340px] bg-slate-900/65 backdrop-blur-2xl border border-slate-700/50 rounded-3xl shadow-[0_0_40px_rgba(0,0,0,0.7)] z-20 flex flex-col overflow-hidden"
            >
              <PanelContent />
            </motion.aside>
          )}
        </AnimatePresence>
      )}

      {/* ── Mobile Bottom Sheet ── */}
      {isMobile && (
        <AnimatePresence>
          {selectedRegionName && (
            <>
              <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="absolute inset-0 bg-black/50 z-30"
                onClick={() => setSelectedRegionName(null)}
              />
              <motion.div
                initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }}
                transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                className="absolute bottom-0 left-0 right-0 h-[75vh] bg-slate-900/96 backdrop-blur-2xl border-t border-slate-700/50 rounded-t-3xl z-40 flex flex-col overflow-hidden"
              >
                <div className="flex justify-center pt-2.5 pb-0.5 shrink-0">
                  <div className="w-10 h-1 bg-slate-600 rounded-full" />
                </div>
                <PanelContent />
              </motion.div>
            </>
          )}
        </AnimatePresence>
      )}

      {/* ── Timeline Footer ── */}
      <footer className="absolute bottom-3 md:bottom-6 left-3 md:left-6 right-3 md:right-6 z-20">
        <motion.div
          initial={{ y: 50, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.2 }}
          className="bg-slate-900/60 backdrop-blur-xl border border-slate-700/50 rounded-2xl md:rounded-3xl p-4 md:p-5 shadow-[0_20px_50px_rgba(0,0,0,0.5)]"
        >
          <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-2 uppercase tracking-widest">
            <span className="text-blue-400">{timeSlots[0]?.label} (зараз)</span>
            <span>+12 год</span>
            <span>{timeSlots[23]?.label} (+24 год)</span>
          </div>

          {/* Intensity bars */}
          <div className="flex justify-between mb-1.5 px-[1%]">
            {timeSlots.map((slot, i) => {
              const probs   = Object.values(predictionData).map(r => r?.[slot.label] ?? 0);
              const avg     = probs.reduce((a, b) => a + b, 0) / Math.max(1, probs.length);
              const isNow   = i === selectedHourOffset;
              return (
                <div key={i} className="flex-1 flex justify-center items-end" style={{ height: '18px' }}>
                  <div
                    className="w-[3px] rounded-full transition-all duration-300"
                    style={{
                      height: Math.max(3, avg * 18) + 'px',
                      backgroundColor: isNow ? '#60a5fa' : probToBarColor(avg),
                      boxShadow: isNow ? '0 0 4px rgba(96,165,250,0.8)' : undefined,
                    }}
                  />
                </div>
              );
            })}
          </div>

          <input
            type="range" min="0" max="23"
            value={selectedHourOffset}
            onChange={e => setSelectedHourOffset(parseInt(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500 mb-1.5"
          />

          {/* Hour labels */}
          <div className="flex justify-between px-[1%]">
            {timeSlots.map((slot, i) => {
              const show = isMobile ? i % 6 === 0 : i % 3 === 0;
              return (
                <div key={i} className="flex-1 flex justify-center">
                  {show && (
                    <span className={`text-[9px] font-mono ${i === selectedHourOffset ? 'text-blue-400 font-bold' : 'text-slate-500'}`}>
                      {slot.label.slice(0, 2)}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </motion.div>
      </footer>
    </div>
  );
}