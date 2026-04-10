"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { ComposableMap, Geographies, Geography } from 'react-simple-maps';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield, ShieldAlert, Clock, Activity, X, Map as MapIcon,
  RefreshCw, BarChart2, TrendingUp, AlertTriangle
} from 'lucide-react';

const GEO_URL = "/Ukraine-regions.json";

const generateMockPredictions = (baseDate) => {
  const regions = [
    "Черкаська область", "Чернігівська область", "Чернівецька область",
    "Автономна Республіка Крим", "Дніпропетровська область", "Донецька область",
    "Івано-Франківська область", "Харківська область", "Херсонська область",
    "Хмельницька область", "Київська область", "Київ", "Кіровоградська область",
    "Луганська область", "Львівська область", "Миколаївська область",
    "Одеська область", "Полтавська область", "Рівненська область",
    "Севастополь", "Сумська область", "Тернопільська область",
    "Закарпатська область", "Вінницька область", "Волинська область",
    "Запорізька область", "Житомирська область"
  ];

  const highRisk = ["Донецька область", "Харківська область", "Запорізька область", "Луганська область", "Херсонська область"];
  const medRisk = ["Дніпропетровська область", "Миколаївська область", "Сумська область", "Чернігівська область"];

  return regions.reduce((acc, name) => {
    const alarms = {};
    for (let i = 0; i < 24; i++) {
      const hourDate = new Date(baseDate.getTime() + i * 60 * 60 * 1000);
      const timeStr = `${String(hourDate.getHours()).padStart(2, '0')}:00`;
      const prob = highRisk.includes(name) ? 0.65 : medRisk.includes(name) ? 0.35 : 0.15;
      alarms[timeStr] = Math.random() < prob ? 1 : 0;
    }
    acc[name] = alarms;
    return acc;
  }, {});
};

export default function TacticalDashboard() {
  const [currentTime, setCurrentTime] = useState(null);
  const [predictionData, setPredictionData] = useState({});
  const [selectedHourOffset, setSelectedHourOffset] = useState(0);
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

  const loadData = useCallback(() => {
    if (!currentTime) return;
    setIsRefreshing(true);
    // Імітація завантаження для гарної анімації
    setTimeout(() => {
      setPredictionData(generateMockPredictions(currentTime));
      setIsRefreshing(false);
    }, 600);
  }, [currentTime]);

  useEffect(() => {
    if (currentTime) loadData();
  }, [currentTime, loadData]);

  const selectedTimeStr = useMemo(() => {
    if (!currentTime) return '00:00';
    const t = new Date(currentTime.getTime() + selectedHourOffset * 60 * 60 * 1000);
    return `${String(t.getHours()).padStart(2, '0')}:00`;
  }, [currentTime, selectedHourOffset]);

  const alarmsCount = useMemo(() => {
    if (!Object.keys(predictionData).length) return 0;
    return Object.values(predictionData).filter(r => r?.[selectedTimeStr] === 1).length;
  }, [predictionData, selectedTimeStr]);

  const stats = useMemo(() => {
    if (!Object.keys(predictionData).length) return null;

    const regions = Object.values(predictionData);
    const totalRegions = regions.length;
    const alarmed = regions.filter(r => r?.[selectedTimeStr] === 1).length;

    // Аналітика: Тренд на 24 години
    const trend24h = [];
    for(let i=0; i<24; i++) {
        const t = new Date(currentTime.getTime() + i * 60 * 60 * 1000);
        const ts = `${String(t.getHours()).padStart(2, '0')}:00`;
        const count = regions.filter(r => r?.[ts] === 1).length;
        trend24h.push(count);
    }

    // Аналітика: Топ 3 найнебезпечніших регіони за добу
    const regionTotals = Object.entries(predictionData).map(([name, hours]) => ({
      name,
      totalAlarms: Object.values(hours).reduce((sum, val) => sum + val, 0)
    }));
    const topDangerRegions = regionTotals.sort((a, b) => b.totalAlarms - a.totalAlarms).slice(0, 3);

    return { alarmed, safe: totalRegions - alarmed, total: totalRegions, trend24h, topDangerRegions };
  }, [predictionData, selectedTimeStr, currentTime]);

  const selectedRegionData = selectedRegionName ? predictionData[selectedRegionName] : null;
  const selectedRegionTotalHours = selectedRegionData ? Object.values(selectedRegionData).reduce((a,b)=>a+b, 0) : 0;

  if (!currentTime || !Object.keys(predictionData).length) {
    return (
      <div className="bg-[#050B14] text-emerald-500 min-h-screen flex flex-col items-center justify-center font-mono gap-3">
        <Activity size={32} className="animate-pulse" />
        <span className="text-sm tracking-widest uppercase">Ініціалізація системи...</span>
      </div>
    );
  }

  const PanelContent = () => (
    <>
      <div className="p-4 md:p-6 bg-slate-800/30 border-b border-slate-700/50 flex justify-between items-start shrink-0 relative overflow-hidden">
        {/* Фоновий градієнт небезпеки залежно від загальної кількості тривог */}
        <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/10 blur-3xl rounded-full -mr-10 -mt-10 pointer-events-none" />

        <div className="relative z-10">
          <h3 className="text-lg md:text-2xl font-bold text-white leading-tight">{selectedRegionName}</h3>
          <div className="flex items-center gap-3 mt-2">
            <p className="text-[10px] text-blue-400 font-mono uppercase tracking-widest flex items-center gap-1 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
              <MapIcon size={10} /> Погодинно
            </p>
            <p className="text-[10px] text-rose-400 font-mono uppercase tracking-widest flex items-center gap-1 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
              <AlertTriangle size={10} /> {selectedRegionTotalHours} год. сумарно
            </p>
          </div>
        </div>
        <button
          onClick={() => setSelectedRegionName(null)}
          className="text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-700 p-2 rounded-full transition-colors border border-slate-600/50 shrink-0 relative z-10"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 md:p-4 space-y-2 custom-scrollbar relative">
        {selectedRegionData
          ? Object.entries(selectedRegionData).map(([time, status], idx) => {
              const isCurrent = idx === selectedHourOffset;
              const hasAlarm = status === 1;
              return (
                <button
                  key={time}
                  onClick={() => setSelectedHourOffset(idx)}
                  className={`w-full flex items-center justify-between p-3 rounded-xl transition-all duration-200 text-left relative overflow-hidden
                    ${isCurrent
                      ? 'bg-slate-800 ring-1 ring-blue-500/60 shadow-[0_0_12px_rgba(59,130,246,0.2)]'
                      : 'hover:bg-slate-800/50 bg-slate-800/20'
                    }`}
                >
                  {/* Міні-індикатор інтенсивності позаду тексту */}
                  {hasAlarm && <div className="absolute left-0 top-0 bottom-0 w-1 bg-rose-500/80 rounded-l-xl" />}

                  <span className={`font-mono text-sm ml-2 ${isCurrent ? 'text-blue-300' : 'text-slate-300'}`}>{time}</span>
                  {hasAlarm ? (
                    <div className="flex items-center gap-1.5 text-rose-400 bg-rose-500/10 px-2.5 py-1 rounded-md border border-rose-500/20 shadow-[0_0_10px_rgba(225,29,72,0.2)]">
                      <ShieldAlert size={12} />
                      <span className="text-[11px] font-bold tracking-wide">ТРИВОГА</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-emerald-400/70 opacity-60">
                      <Shield size={12} />
                      <span className="text-[11px] font-medium tracking-wide">БЕЗПЕЧНО</span>
                    </div>
                  )}
                </button>
              );
            })
          : <div className="text-slate-500 text-sm p-4 text-center">Немає даних.</div>
        }
      </div>
    </>
  );

  return (
    <div className="relative min-h-screen bg-[#050B14] text-slate-100 font-sans overflow-hidden flex flex-col selection:bg-rose-500/30">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-950/20 via-[#050B14] to-[#050B14] pointer-events-none" />

      {/* Header */}
      <header className="absolute top-3 md:top-6 left-3 md:left-6 right-3 md:right-6 z-20 flex justify-between items-start gap-2 pointer-events-none">
        <motion.div
          initial={{ y: -40, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
          className="bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 p-3 md:p-5 rounded-xl md:rounded-2xl shadow-xl pointer-events-auto flex items-center gap-3 md:gap-5 min-w-0"
        >
          <div className="relative flex items-center justify-center w-9 h-9 md:w-12 md:h-12 bg-rose-500/10 rounded-full border border-rose-500/30 shrink-0">
            <Activity className="text-rose-500 animate-pulse" size={isMobile ? 18 : 24} />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm md:text-xl font-bold tracking-tight text-white truncate">Система Прогнозування</h1>
            <div className="flex flex-wrap items-center gap-2 mt-0.5">
              <span className="text-[10px] text-emerald-400 font-mono bg-emerald-400/10 px-2 py-0.5 rounded-md border border-emerald-400/20 flex items-center gap-1">
                Модель Активна
              </span>
              <span className="text-[10px] text-slate-400 font-mono hidden sm:block">Тривог зараз: {alarmsCount}</span>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ y: -40, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.1 }}
          className="flex items-start gap-2 pointer-events-auto"
        >
          <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 px-3 md:px-5 py-2.5 md:py-4 rounded-xl md:rounded-2xl shadow-xl flex items-center gap-2">
            <Clock size={16} className="text-blue-400 shrink-0" />
            <div className="flex flex-col">
              <span className="text-[9px] text-slate-400 uppercase tracking-widest font-bold hidden md:block">Прогноз</span>
              <span className="font-mono text-sm md:text-lg tracking-wider text-white font-semibold">{selectedTimeStr}</span>
            </div>
          </div>

          <button
            onClick={() => setShowStats(s => !s)}
            className={`bg-slate-900/50 backdrop-blur-xl border p-2.5 md:p-3.5 rounded-xl md:rounded-2xl shadow-xl transition-colors ${showStats ? 'border-blue-500/50 text-blue-400' : 'border-slate-700/50 text-slate-400 hover:text-white'}`}
          >
            <BarChart2 size={16} />
          </button>

          <button
            onClick={loadData}
            disabled={isRefreshing}
            className="bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 p-2.5 md:p-3.5 rounded-xl md:rounded-2xl shadow-xl text-slate-400 hover:text-white transition-colors disabled:opacity-50"
          >
            <RefreshCw size={16} className={isRefreshing ? 'animate-spin' : ''} />
          </button>
        </motion.div>
      </header>

      {/* Просунута панель Аналітики */}
      <AnimatePresence>
        {showStats && stats && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -8, scale: 0.95 }}
            className="absolute top-20 md:top-24 right-3 md:right-6 z-30 w-80 bg-slate-900/90 backdrop-blur-2xl border border-slate-700/50 rounded-2xl shadow-2xl p-5 flex flex-col gap-5"
          >
            {/* Блок 1: Поточний стан */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-2 flex items-center gap-2"><Activity size={14} className="text-blue-400"/> Статус на {selectedTimeStr}</h4>
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-3 flex flex-col items-center justify-center">
                  <div className="text-3xl font-bold text-rose-400 font-mono">{stats.alarmed}</div>
                  <div className="text-[10px] text-rose-400/70 uppercase tracking-wide mt-1">В тривозі</div>
                </div>
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3 flex flex-col items-center justify-center">
                  <div className="text-3xl font-bold text-emerald-400 font-mono">{stats.safe}</div>
                  <div className="text-[10px] text-emerald-400/70 uppercase tracking-wide mt-1">Безпечно</div>
                </div>
              </div>
              <div className="mt-3 bg-slate-800/50 rounded-lg p-2.5">
                <div className="flex justify-between text-[10px] text-slate-400 mb-1.5 uppercase tracking-wide">
                  <span>Охоплення території</span>
                  <span className="text-rose-400 font-bold">{Math.round((stats.alarmed / stats.total) * 100)}%</span>
                </div>
                <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-rose-600 to-rose-400 rounded-full"
                    initial={{ width: 0 }} animate={{ width: `${(stats.alarmed / stats.total) * 100}%` }} transition={{ duration: 0.8, ease: 'easeOut' }}
                  />
                </div>
              </div>
            </div>

            {/* Блок 2: 24-годинний тренд (Міні-графік) */}
            <div className="border-t border-slate-700/50 pt-4">
              <h4 className="text-xs font-semibold text-slate-300 mb-3 flex items-center gap-2"><TrendingUp size={12} className="text-emerald-400"/> Динаміка за 24 години</h4>
              <div className="flex items-end gap-0.5 h-12">
                {stats.trend24h.map((count, i) => {
                  const heightPercent = (count / stats.total) * 100;
                  const isCurrentHour = i === selectedHourOffset;
                  return (
                    <div key={i} className="flex-1 flex flex-col justify-end group relative h-full">
                      <div
                        className={`w-full rounded-t-sm transition-all duration-300 ${isCurrentHour ? 'bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.8)]' : (count > 0 ? 'bg-rose-500/60 group-hover:bg-rose-400' : 'bg-slate-700')}`}
                        style={{ height: `${Math.max(10, heightPercent)}%` }}
                      />
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Блок 3: Топ-3 найнебезпечніші */}
            <div className="border-t border-slate-700/50 pt-4">
              <h4 className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-2"><AlertTriangle size={12} className="text-amber-400"/> Топ зон ризику (доба)</h4>
              <div className="space-y-1.5">
                {stats.topDangerRegions.map((region, idx) => (
                  <div key={region.name} className="flex justify-between items-center bg-slate-800/40 p-2 rounded-lg">
                    <span className="text-[11px] text-slate-300 truncate pr-2"><span className="text-slate-500 mr-1">{idx + 1}.</span>{region.name}</span>
                    <span className="text-[10px] font-mono text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded">{region.totalAlarms} год</span>
                  </div>
                ))}
              </div>
            </div>

          </motion.div>
        )}
      </AnimatePresence>

      {/* Map */}
      <main className="flex-1 flex items-center justify-center relative z-0 w-full pt-20 pb-36 md:pt-24 md:pb-36 px-2">
        <ComposableMap
          projection="geoMercator"
          projectionConfig={{ scale: isMobile ? 1600 : 2400, center: [31.5, 48.5] }}
          className="w-full max-w-6xl h-auto"
        >
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const regionName = geo.properties.NAME_1;
                const hasAlarm = predictionData[regionName]?.[selectedTimeStr] === 1;
                const isSelected = selectedRegionName === regionName;

                return (
                  <Geography
                    key={geo.rsmKey || regionName}
                    geography={geo}
                    onClick={() => {
                      setSelectedRegionName(regionName);
                      setShowStats(false);
                    }}
                    className="transition-all duration-300 focus:outline-none"
                    style={{
                      default: {
                        fill: hasAlarm ? '#7f1d1d' : '#1e293b',
                        stroke: isSelected ? '#60a5fa' : hasAlarm ? '#ef4444' : '#334155',
                        strokeWidth: isSelected ? 1.5 : 0.5,
                        outline: 'none',
                      },
                      hover: {
                        fill: hasAlarm ? '#991b1b' : '#334155',
                        stroke: '#94a3b8',
                        strokeWidth: 1,
                        outline: 'none',
                        cursor: 'pointer',
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

      {/* Desktop Sidebar */}
      {!isMobile && (
        <AnimatePresence>
          {selectedRegionName && (
            <motion.aside
              initial={{ x: 400, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 400, opacity: 0 }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="absolute right-6 top-28 bottom-36 w-80 bg-slate-900/60 backdrop-blur-2xl border border-slate-700/50 rounded-3xl shadow-[0_0_40px_rgba(0,0,0,0.7)] z-20 flex flex-col overflow-hidden"
            >
              <PanelContent />
            </motion.aside>
          )}
        </AnimatePresence>
      )}

      {/* Mobile Bottom Sheet */}
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
                className="absolute bottom-0 left-0 right-0 h-[60vh] bg-slate-900/95 backdrop-blur-2xl border-t border-slate-700/50 rounded-t-3xl z-40 flex flex-col overflow-hidden"
              >
                <div className="flex justify-center pt-3 pb-1 shrink-0">
                  <div className="w-10 h-1 bg-slate-600 rounded-full" />
                </div>
                <PanelContent />
              </motion.div>
            </>
          )}
        </AnimatePresence>
      )}

      {/* Timeline Footer */}
      <footer className="absolute bottom-3 md:bottom-6 left-3 md:left-6 right-3 md:right-6 z-20">
        <motion.div
          initial={{ y: 50, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.2 }}
          className="bg-slate-900/60 backdrop-blur-xl border border-slate-700/50 rounded-2xl md:rounded-3xl p-4 md:p-6 shadow-[0_20px_50px_rgba(0,0,0,0.5)]"
        >
          <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-3 md:mb-4 uppercase tracking-widest">
            <span className="text-blue-400">Зараз</span>
            <span>+12 год</span>
            <span>+24 год</span>
          </div>

          <div className="flex justify-between mb-2 px-[1%]">
            {[...Array(24)].map((_, i) => {
              const t = new Date(currentTime.getTime() + i * 60 * 60 * 1000);
              const ts = `${String(t.getHours()).padStart(2, '0')}:00`;
              const alarmCount = Object.values(predictionData).filter(r => r?.[ts] === 1).length;
              const intensity = alarmCount / Math.max(1, Object.keys(predictionData).length);
              return (
                <div key={i} className="flex-1 flex justify-center items-end" style={{ height: '20px' }}>
                  <div
                    className="w-[3px] rounded-full transition-all duration-300"
                    style={{
                      height: Math.max(3, intensity * 20) + 'px',
                      backgroundColor: intensity > 0.25
                        ? `rgba(239,68,68,${0.35 + intensity * 0.65})`
                        : 'rgba(51,65,85,0.5)',
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
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500 mb-2"
          />

          <div className="flex justify-between px-[1%]">
            {[...Array(24)].map((_, i) => {
              const t = new Date(currentTime.getTime() + i * 60 * 60 * 1000);
              const label = String(t.getHours()).padStart(2, '0');
              const show = isMobile ? i % 6 === 0 : i % 3 === 0;
              return (
                <div key={i} className="flex-1 flex justify-center">
                  {show && (
                    <span className={`text-[9px] font-mono ${i === selectedHourOffset ? 'text-blue-400 font-bold' : 'text-slate-500'}`}>
                      {label}
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