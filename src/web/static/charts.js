async function renderChart(el) {
  const chartKey = el.dataset.chart;
  const apiBase = el.dataset.api || "/api/charts";
  const response = await fetch(`${apiBase}/${chartKey}`);
  if (!response.ok) {
    el.textContent = "图表数据暂不可用";
    return;
  }

  const payload = await response.json();
  const chart = echarts.init(el);
  const yAxis = payload.series.some((item) => item.axis === "right")
    ? [{ type: "value" }, { type: "value" }]
    : [{ type: "value" }];

  const option = {
    title: { text: payload.title, left: 8, top: 8, textStyle: { fontSize: 14 } },
    tooltip: { trigger: "axis" },
    legend: { top: 36 },
    grid: { left: 48, right: 48, top: 78, bottom: 42 },
    xAxis: { type: "category", data: payload.x_axis },
    yAxis,
    series: payload.series.map((item) => ({
      name: item.name,
      type: "line",
      smooth: true,
      yAxisIndex: item.axis === "right" ? 1 : 0,
      data: item.data,
    })),
  };

  if (payload.chart_type === "bar") {
    option.xAxis = { type: "category", data: payload.x_axis, axisLabel: { rotate: 28 } };
    option.series = payload.series.map((item) => ({
      name: item.name,
      type: "bar",
      data: item.data,
    }));
  }

  if (payload.chart_type === "pie") {
    const values = payload.series[0]?.data || [];
    option.tooltip = { trigger: "item" };
    option.grid = undefined;
    option.xAxis = undefined;
    option.yAxis = undefined;
    option.series = [
      {
        name: payload.series[0]?.name || payload.title,
        type: "pie",
        radius: ["38%", "68%"],
        center: ["50%", "58%"],
        data: (payload.x_axis || []).map((name, index) => ({ name, value: values[index] })),
      },
    ];
  }

  chart.setOption(option);
  window.addEventListener("resize", () => chart.resize());
}

document.querySelectorAll(".chart").forEach((el) => {
  renderChart(el).catch(() => {
    el.textContent = "图表渲染失败";
  });
});
