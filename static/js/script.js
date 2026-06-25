(function () {
    const clockEl = document.getElementById("realTimeClock");

    function updateClock() {
        if (!clockEl) return;
        const now = new Date();
        const date = now.toLocaleDateString("id-ID", {
            weekday: "long",
            day: "2-digit",
            month: "long",
            year: "numeric"
        });
        const time = now.toLocaleTimeString("id-ID", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
        });

        clockEl.innerHTML = `
            <strong>${date}</strong><br>
            <span>${time} WIB</span>
        `;
    }

    updateClock();
    setInterval(updateClock, 1000);

    const passwordToggle = document.querySelector("[data-toggle-password]");
    const passwordInput = document.getElementById("passwordInput");
    if (passwordToggle && passwordInput) {
        passwordToggle.addEventListener("click", () => {
            const isPassword = passwordInput.type === "password";
            passwordInput.type = isPassword ? "text" : "password";
            passwordToggle.setAttribute("aria-label", isPassword ? "Sembunyikan password" : "Tampilkan password");
            passwordToggle.classList.toggle("is-active", isPassword);
        });
    }

    const loginForm = document.querySelector("[data-login-form]");
    if (loginForm) {
        loginForm.addEventListener("submit", () => {
            const submit = loginForm.querySelector(".login-submit");
            if (submit) {
                submit.classList.add("is-loading");
                submit.setAttribute("disabled", "disabled");
            }
        });
    }

    function parseDate(value) {
        if (!value) return null;
        const normalized = value.includes("T") ? value : value.replace(" ", "T");
        const parsed = new Date(normalized);
        if (!Number.isNaN(parsed.getTime())) return parsed;
        return null;
    }

    function updateRelativeTimes() {
        document.querySelectorAll(".relative-time").forEach((el) => {
            const parsed = parseDate(el.dataset.time || el.getAttribute("datetime"));
            if (!parsed) return;
            const seconds = Math.max(1, Math.floor((Date.now() - parsed.getTime()) / 1000));
            const units = [
                ["tahun", 31536000],
                ["bulan", 2592000],
                ["hari", 86400],
                ["jam", 3600],
                ["menit", 60],
                ["detik", 1]
            ];
            const match = units.find(([, unitSeconds]) => seconds >= unitSeconds);
            const amount = Math.floor(seconds / match[1]);
            el.textContent = `${amount} ${match[0]} lalu`;
        });
    }

    updateRelativeTimes();
    setInterval(updateRelativeTimes, 30000);

    const chartDataEl = document.getElementById("dashboardChartData");
    if (!chartDataEl || typeof Chart === "undefined") return;

    let dashboardData = null;
    try {
        dashboardData = JSON.parse(chartDataEl.textContent);
    } catch (error) {
        console.warn("Dashboard chart data tidak valid.", error);
        return;
    }

    const colors = ["#16A34A", "#22C55E", "#84CC16", "#0F766E", "#14B8A6", "#F59E0B", "#6366F1", "#94A3B8"];
    const gridColor = "rgba(20, 83, 45, 0.08)";
    const textColor = "#334155";

    Chart.defaults.font.family = 'Inter, "Segoe UI", system-ui, sans-serif';
    Chart.defaults.color = textColor;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;

    function makeGradient(ctx, top = "#22C55E", bottom = "rgba(34, 197, 94, 0.08)") {
        const gradient = ctx.createLinearGradient(0, 0, 0, 260);
        gradient.addColorStop(0, top);
        gradient.addColorStop(1, bottom);
        return gradient;
    }

    function renderCategoryPie() {
        const el = document.getElementById("categoryPieChart");
        if (!el || !dashboardData.categories.length) return;
        new Chart(el, {
            type: "pie",
            data: {
                labels: dashboardData.categories.map((item) => item.label),
                datasets: [{
                    data: dashboardData.categories.map((item) => item.count),
                    backgroundColor: colors,
                    borderColor: "#ffffff",
                    borderWidth: 4,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 900, easing: "easeOutQuart" },
                plugins: {
                    legend: { position: "right" },
                    tooltip: {
                        callbacks: {
                            label(context) {
                                const item = dashboardData.categories[context.dataIndex];
                                return `${item.count} Data • ${item.percentage}%`;
                            },
                            title(context) {
                                return context[0].label;
                            }
                        }
                    }
                }
            }
        });
    }

    function renderCategoryBar() {
        const el = document.getElementById("categoryBarChart");
        if (!el || !dashboardData.categories.length) return;
        const ctx = el.getContext("2d");
        new Chart(el, {
            type: "bar",
            data: {
                labels: dashboardData.categories.map((item) => item.label),
                datasets: [{
                    label: "Jumlah Analisis",
                    data: dashboardData.categories.map((item) => item.count),
                    backgroundColor: makeGradient(ctx),
                    borderColor: "#16A34A",
                    borderWidth: 1,
                    borderRadius: 14,
                    maxBarThickness: 52
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 850, easing: "easeOutQuart" },
                scales: {
                    x: { grid: { display: false } },
                    y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: gridColor } }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label(context) {
                                return `${context.raw} analisis`;
                            }
                        }
                    }
                }
            }
        });
    }

    function renderTrendLine() {
        const el = document.getElementById("trendLineChart");
        if (!el) return;
        const ctx = el.getContext("2d");
        new Chart(el, {
            type: "line",
            data: {
                labels: dashboardData.trend.map((item) => item.label),
                datasets: [{
                    label: "Analisis per Hari",
                    data: dashboardData.trend.map((item) => item.count),
                    borderColor: "#16A34A",
                    backgroundColor: makeGradient(ctx, "rgba(22, 163, 74, 0.28)", "rgba(22, 163, 74, 0.02)"),
                    fill: true,
                    tension: 0.42,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    pointBackgroundColor: "#ffffff",
                    pointBorderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 900, easing: "easeOutQuart" },
                scales: {
                    x: { grid: { display: false } },
                    y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: gridColor } }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label(context) {
                                return `${context.raw} analisis`;
                            }
                        }
                    }
                }
            }
        });
    }

    function renderPotentialDonut() {
        const el = document.getElementById("potentialDonutChart");
        if (!el || !dashboardData.potential.some((item) => item.count > 0)) return;
        new Chart(el, {
            type: "doughnut",
            data: {
                labels: dashboardData.potential.map((item) => item.label),
                datasets: [{
                    data: dashboardData.potential.map((item) => item.count),
                    backgroundColor: ["#16A34A", "#F59E0B", "#2563EB", "#EF4444"],
                    borderColor: "#ffffff",
                    borderWidth: 5,
                    cutout: "66%",
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 900, easing: "easeOutQuart" },
                plugins: {
                    legend: { position: "bottom" },
                    tooltip: {
                        callbacks: {
                            label(context) {
                                const count = context.raw || 0;
                                const percent = dashboardData.total ? ((count / dashboardData.total) * 100).toFixed(1) : 0;
                                return `${count} data • ${percent}%`;
                            }
                        }
                    }
                }
            }
        });
    }

    renderCategoryPie();
    renderCategoryBar();
    renderTrendLine();
    renderPotentialDonut();
})();
