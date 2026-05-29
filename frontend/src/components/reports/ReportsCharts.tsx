"use client";

import { useTranslations } from "next-intl";
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useFormat } from "@/lib/useFormat";

const PALETTE = [
  "#1a1a1a",
  "#c2410c",
  "#3d3d3d",
  "#6b6660",
  "#a8a8a8",
  "#606060",
  "#848484",
  "#e8e3dc",
];

interface MonthlyDatum {
  month: string;
  total: number;
}

interface CategoryDatum {
  name: string;
  value: number;
}

interface Props {
  monthlyData: MonthlyDatum[];
  categoryData: CategoryDatum[];
  categoryTitle: string;
  loading: boolean;
  mode?: "monthly" | "annual";
}

export function ReportsCharts({ monthlyData, categoryData, categoryTitle, loading, mode = "monthly" }: Props) {
  const t = useTranslations("reports");
  const { formatCurrency } = useFormat();
  if (loading) {
    return <p className="text-sm text-ink-muted">{t("loadingCharts")}</p>;
  }

  const noCategoryDataKey = mode === "annual" ? "noExpensesThisYear" : "noExpensesThisMonth";

  return (
    <div className="space-y-6">
      {/* Bar chart — annual only */}
      {mode === "annual" && (
        <div className="bg-paper-card border border-paper-line rounded p-6 shadow-card">
          <h2 className="font-display text-xl text-ink mb-4">{t("spendingByMonth")}</h2>
          {monthlyData.every((d) => d.total === 0) ? (
            <p className="text-sm text-ink-muted">{t("noDataThisYear")}</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={monthlyData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <XAxis
                  dataKey="month"
                  tick={{ fontSize: 11, fill: "#6b6660" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={(v) => formatCurrency(v as number)}
                  width={80}
                  tick={{ fontSize: 11, fill: "#6b6660" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  formatter={(v) => [formatCurrency(v as number), t("total")]}
                  cursor={{ fill: "rgba(0,0,0,0.04)" }}
                  contentStyle={{
                    background: "#f5f0e8",
                    border: "1px solid #e0d9ce",
                    borderRadius: "4px",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="total" fill="#1a1a1a" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      )}

      {/* Donut chart — by category */}
      <div className="bg-paper-card border border-paper-line rounded p-6 shadow-card">
        <h2 className="font-display text-xl text-ink mb-4">{categoryTitle}</h2>
        {categoryData.length === 0 ? (
          <p className="text-sm text-ink-muted">{t(noCategoryDataKey)}</p>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={categoryData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius="50%"
                outerRadius="75%"
                paddingAngle={2}
              >
                {categoryData.map((_, i) => (
                  <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v) => [formatCurrency(v as number), ""]}
                contentStyle={{
                  background: "#f5f0e8",
                  border: "1px solid #e0d9ce",
                  borderRadius: "4px",
                  fontSize: "12px",
                }}
              />
              <Legend
                iconType="circle"
                iconSize={8}
                formatter={(name) => (
                  <span style={{ fontSize: 12, color: "#6b6660" }}>{name}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
