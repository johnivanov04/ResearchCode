"use client";

import { type PointerEvent, useId, useState } from "react";
import type { ScenarioResult } from "@/lib/growth";

const WIDTH = 640;
const HEIGHT = 320;
const MARGIN = { top: 16, right: 16, bottom: 44, left: 56 };
const PLOT_W = WIDTH - MARGIN.left - MARGIN.right;
const PLOT_H = HEIGHT - MARGIN.top - MARGIN.bottom;

function niceTicks(min: number, max: number, count = 5): number[] {
  const span = max - min || 1;
  const rawStep = span / count;
  const magnitude = 10 ** Math.floor(Math.log10(rawStep));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => span / s <= count) ?? rawStep;
  const ticks: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + step * 1e-9; v += step) {
    ticks.push(Number(v.toFixed(10)));
  }
  return ticks;
}

function formatTick(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

/**
 * Transformed growth curve with the fitted line. Hover or tap to inspect a
 * reading; the same data is available as a table for non-visual access.
 */
export function GrowthChart({ result }: { result: ScenarioResult }) {
  const [hover, setHover] = useState<number | null>(null);
  const titleId = useId();
  const { points, fit, scenario } = result;

  const xMax = 12;
  const ys = points.map((p) => p.y);
  const yPad = (Math.max(...ys) - Math.min(...ys)) * 0.08;
  const yMin = Math.floor((Math.min(...ys) - yPad) * 2) / 2;
  const yMax = Math.ceil((Math.max(...ys) + yPad) * 2) / 2;

  const sx = (x: number) => MARGIN.left + (x / xMax) * PLOT_W;
  const sy = (y: number) => MARGIN.top + (1 - (y - yMin) / (yMax - yMin)) * PLOT_H;
  const xTicks = [0, 2, 4, 6, 8, 10, 12];
  const yTicks = niceTicks(yMin, yMax);

  const fitY = (x: number) => fit.intercept + fit.slope * x;
  const lineStart = fit.startH;
  const lineEnd = fit.endH;

  function onPointerMove(event: PointerEvent<SVGRectElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const xValue = ((event.clientX - rect.left) / rect.width) * xMax;
    let nearest = 0;
    for (let i = 1; i < points.length; i++) {
      if (Math.abs(points[i].timeH - xValue) < Math.abs(points[nearest].timeH - xValue)) nearest = i;
    }
    setHover(nearest);
  }

  const hovered = hover === null ? undefined : points[hover];

  return (
    <figure aria-labelledby={titleId}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p id={titleId} className="text-sm font-semibold text-ink">
          {scenario.yLabel} over time
        </p>
        <ul className="flex flex-wrap gap-4 text-xs text-body" aria-label="Legend">
          <li className="flex items-center gap-1.5">
            <svg aria-hidden="true" width="10" height="10">
              <circle cx="5" cy="5" r="4" fill="var(--color-series-1)" />
            </svg>
            Readings (synthetic)
          </li>
          <li className="flex items-center gap-1.5">
            <svg aria-hidden="true" width="18" height="10">
              <line x1="1" y1="5" x2="17" y2="5" stroke="var(--color-series-2)" strokeWidth="2" strokeLinecap="round" />
            </svg>
            Fitted line
          </li>
          <li className="flex items-center gap-1.5">
            <span aria-hidden="true" className="inline-block h-2.5 w-4 rounded-sm bg-accent-100" />
            Fit window
          </li>
        </ul>
      </div>

      <div className="relative mt-3">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="h-auto w-full"
          role="img"
          aria-label={`Plot of ${scenario.yLabel} against time in hours for synthetic readings, with a fitted line of slope ${fit.slope.toFixed(3)} between ${fit.startH} and ${fit.endH} hours.`}
        >
          <rect
            x={sx(lineStart)}
            y={MARGIN.top}
            width={Math.max(sx(lineEnd) - sx(lineStart), 2)}
            height={PLOT_H}
            fill="var(--color-accent-100)"
            opacity="0.7"
          />
          {yTicks.map((tick) => (
            <g key={`y${tick}`}>
              <line x1={MARGIN.left} x2={WIDTH - MARGIN.right} y1={sy(tick)} y2={sy(tick)} stroke="var(--color-line)" strokeWidth="1" />
              <text x={MARGIN.left - 8} y={sy(tick)} textAnchor="end" dominantBaseline="middle" fontSize="11" fill="var(--color-muted)">
                {formatTick(tick)}
              </text>
            </g>
          ))}
          {xTicks.map((tick) => (
            <text key={`x${tick}`} x={sx(tick)} y={HEIGHT - MARGIN.bottom + 18} textAnchor="middle" fontSize="11" fill="var(--color-muted)">
              {tick}
            </text>
          ))}
          <line x1={MARGIN.left} x2={WIDTH - MARGIN.right} y1={HEIGHT - MARGIN.bottom} y2={HEIGHT - MARGIN.bottom} stroke="var(--color-navy-200)" />
          <text x={MARGIN.left + PLOT_W / 2} y={HEIGHT - 6} textAnchor="middle" fontSize="12" fill="var(--color-body)">
            Time (hours)
          </text>
          <text
            transform={`translate(14 ${MARGIN.top + PLOT_H / 2}) rotate(-90)`}
            textAnchor="middle"
            fontSize="12"
            fill="var(--color-body)"
          >
            {scenario.yLabel}
          </text>

          {hovered ? (
            <line x1={sx(hovered.timeH)} x2={sx(hovered.timeH)} y1={MARGIN.top} y2={HEIGHT - MARGIN.bottom} stroke="var(--color-navy-200)" strokeDasharray="3 3" />
          ) : null}

          {points.map((p, i) => (
            <circle
              key={p.timeH}
              cx={sx(p.timeH)}
              cy={sy(p.y)}
              r={i === hover ? 5.5 : 4}
              fill="var(--color-series-1)"
              stroke="#ffffff"
              strokeWidth="1.5"
            />
          ))}

          <line
            x1={sx(lineStart)}
            y1={sy(fitY(lineStart))}
            x2={sx(lineEnd)}
            y2={sy(fitY(lineEnd))}
            stroke="var(--color-series-2)"
            strokeWidth="2.5"
            strokeLinecap="round"
          />

          <rect
            x={MARGIN.left}
            y={MARGIN.top}
            width={PLOT_W}
            height={PLOT_H}
            fill="transparent"
            onPointerMove={onPointerMove}
            onPointerLeave={() => setHover(null)}
          />
        </svg>

        {hovered ? (
          <div
            className="pointer-events-none absolute top-2 rounded-md border border-line bg-white px-3 py-2 text-xs shadow-sm"
            style={
              sx(hovered.timeH) > WIDTH / 2
                ? { right: `${100 - (sx(hovered.timeH) / WIDTH) * 100 + 2}%` }
                : { left: `${(sx(hovered.timeH) / WIDTH) * 100 + 2}%` }
            }
          >
            <p className="font-medium text-ink">{(hovered.timeH * 60).toFixed(0)} min</p>
            <p className="text-body">
              {scenario.yLabel}: <span className="font-mono">{hovered.y.toFixed(3)}</span>
            </p>
          </div>
        ) : null}
      </div>
    </figure>
  );
}
