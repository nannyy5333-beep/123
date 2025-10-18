
(function(){
  if (!window.Chart) return;
  Chart.defaults.color = "#e4e7eb";
  Chart.defaults.borderColor = "rgba(255,255,255,.08)";
  // Default palette
  const brand = "#3ecf8e";
  const neutral = "rgba(255,255,255,.55)";
  // If dataset color is not set, apply brand/neutral alternation
  const orig = Chart.controllers.bar.prototype.draw;
  Chart.defaults.elements.bar.borderRadius = 6;
  // Nothing destructive; just defaults for datasets created later
  Chart.defaults.datasets.bar.backgroundColor = "rgba(62,207,142,.28)";
  Chart.defaults.datasets.line.borderColor = brand;
  Chart.defaults.datasets.line.backgroundColor = "rgba(62,207,142,.08)";
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
})();
