async function renderChart(el) {
  const chartKey = el.dataset.chart;
  const response = await fetch(`/api/charts/${chartKey}`);
  if (!response.ok) {
    el.textContent = "图表数据暂不可用";
    return;
  }
  const payload = await response.json();
  const chart = echarts.init(el);
  const yAxis = payload.series.some((item) => item.axis === "right")
    ? [{ type: "value" }, { type: "value" }]
    : [{ type: "value" }];
  chart.setOption({
    title: { text: payload.title, left: 8, top: 8, textStyle: { fontSize: 14 } },
    tooltip: { trigger: "axis" },
    legend: { top: 36 },
    grid: { left: 48, right: 48, top: 78, bottom: 36 },
    xAxis: { type: "category", data: payload.x_axis },
    yAxis,
    series: payload.series.map((item) => ({
      name: item.name,
      type: "line",
      smooth: true,
      yAxisIndex: item.axis === "right" ? 1 : 0,
      data: item.data,
    })),
  });
  window.addEventListener("resize", () => chart.resize());
}

document.querySelectorAll(".chart").forEach((el) => {
  renderChart(el).catch(() => {
    el.textContent = "图表渲染失败";
  });
});
