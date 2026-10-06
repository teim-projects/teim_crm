/**
 * Chart Toolbar & Maximize Manager for TEIM CRM
 */

(function () {
    // Create & Inject Fullscreen Modal HTML structure into DOM if not exists
    function ensureFullscreenModal() {
        if (document.getElementById('chartFullscreenOverlay')) return;

        const modalHTML = `
        <div id="chartFullscreenOverlay" class="chart-fullscreen-overlay">
            <div class="chart-fullscreen-container">
                <div class="chart-fullscreen-header">
                    <h4 id="chartFullscreenTitle"><i class="fa-solid fa-chart-line me-2"></i>Chart Analysis</h4>
                    <button type="button" class="chart-fullscreen-close" onclick="closeChartFullscreen()" title="Close (Esc)">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
                <div class="chart-fullscreen-body" id="chartFullscreenBody">
                    <!-- Target chart clone/canvas will be mounted here -->
                </div>
            </div>
        </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Escape Key listener
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                closeChartFullscreen();
            }
        });
    }

    // Helper: Find chart element and title from button or container ID
    function getChartContext(elementOrId) {
        let container = null;
        let chartEl = null;
        let title = "Chart Details";

        if (typeof elementOrId === 'string') {
            chartEl = document.getElementById(elementOrId);
            if (chartEl) {
                container = chartEl.closest('.chart-card, .pie-chart-container, .bar-chart-container, .chartcontainer, .card');
            }
        } else if (elementOrId instanceof HTMLElement) {
            container = elementOrId.closest('.chart-card, .pie-chart-container, .bar-chart-container, .chartcontainer, .card');
            if (container) {
                chartEl = container.querySelector('canvas, svg, img, .chart-body');
            }
        }

        if (container) {
            const headerTitle = container.querySelector('.chart-card-header span, h3, .card-title, h5');
            if (headerTitle) {
                title = headerTitle.textContent.trim();
            }
        }

        return { container, chartEl, title };
    }

    // Maximize Chart Function
    window.maximizeChart = function (elementOrId) {
        ensureFullscreenModal();

        const { container, chartEl, title } = getChartContext(elementOrId);

        const modalOverlay = document.getElementById('chartFullscreenOverlay');
        const modalBody = document.getElementById('chartFullscreenBody');
        const modalTitle = document.getElementById('chartFullscreenTitle');

        modalTitle.innerHTML = `<i class="fa-solid fa-chart-line me-2"></i> ${title}`;
        modalBody.innerHTML = ''; // Clear previous

        const targetNode = chartEl || container;

        if (!targetNode) {
            modalBody.innerHTML = '<p class="text-muted">Unable to locate chart element.</p>';
            modalOverlay.classList.add('active');
            return;
        }

        try {
            if (targetNode.tagName === 'CANVAS') {
                let rendered = false;

                // Find if there are side legend/control blocks in container (like stateLeadCanvas, prodVsSvcPieCanvas)
                const sideControls = container ? container.querySelector('div[style*="width: 155px"], div[style*="width: 150px"], div[style*="width: 160px"], div[style*="width: 175px"]') : null;

                const flexWrap = document.createElement('div');
                flexWrap.style.width = '100%';
                flexWrap.style.height = '100%';
                flexWrap.style.display = 'flex';
                flexWrap.style.alignItems = 'center';
                flexWrap.style.justifyContent = 'space-between';
                flexWrap.style.gap = '20px';
                flexWrap.style.boxSizing = 'border-box';

                const canvasWrap = document.createElement('div');
                canvasWrap.style.flex = '1';
                canvasWrap.style.height = '100%';
                canvasWrap.style.position = 'relative';
                canvasWrap.style.minWidth = '0';

                const newCanvas = document.createElement('canvas');
                canvasWrap.appendChild(newCanvas);
                flexWrap.appendChild(canvasWrap);

                if (sideControls) {
                    const sideClone = sideControls.cloneNode(true);
                    sideClone.style.fontSize = '14px';
                    sideClone.style.paddingLeft = '15px';
                    flexWrap.appendChild(sideClone);
                }

                modalBody.appendChild(flexWrap);

                // Try rendering active Chart.js instance in full screen
                if (window.Chart) {
                    const chartInstance = (typeof Chart.getChart === 'function' ? Chart.getChart(targetNode) : null) || targetNode._chart;
                    if (chartInstance && chartInstance.config) {
                        new Chart(newCanvas.getContext('2d'), {
                            type: chartInstance.config.type,
                            data: chartInstance.config.data,
                            options: Object.assign({}, chartInstance.config.options || {}, {
                                responsive: true,
                                maintainAspectRatio: false,
                                animation: { duration: 250 }
                            })
                        });
                        rendered = true;
                    }
                }

                // Fallback: Render crisp canvas bitmap image snapshot
                if (!rendered && targetNode.toDataURL) {
                    const img = document.createElement('img');
                    img.src = targetNode.toDataURL('image/png');
                    img.alt = title;
                    img.style.maxWidth = '98%';
                    img.style.maxHeight = '98%';
                    img.style.objectFit = 'contain';
                    modalBody.innerHTML = '';
                    modalBody.appendChild(img);
                }
            } else if (container && (container.querySelector('svg') || container.querySelector('.treemap-container'))) {
                // For SVG Funnels or Treemap: clone the chart-body container completely
                const chartBody = container.querySelector('.chart-body') || container;
                const clone = chartBody.cloneNode(true);
                clone.style.width = '100%';
                clone.style.height = '100%';
                clone.style.maxWidth = '100%';
                clone.style.maxHeight = '100%';
                clone.style.boxSizing = 'border-box';
                clone.style.overflow = 'auto';
                modalBody.appendChild(clone);
            } else {
                // Clone SVG, Div, or Image
                const clone = targetNode.cloneNode(true);
                clone.style.width = '100%';
                clone.style.height = '100%';
                clone.style.maxWidth = '100%';
                clone.style.maxHeight = '100%';
                clone.style.boxSizing = 'border-box';
                modalBody.appendChild(clone);
            }
        } catch (err) {
            console.error('Error maximizing chart:', err);
            // Emergency fallback: Image snapshot
            if (targetNode && targetNode.toDataURL) {
                const img = document.createElement('img');
                img.src = targetNode.toDataURL('image/png');
                img.style.maxWidth = '98%';
                img.style.maxHeight = '98%';
                img.style.objectFit = 'contain';
                modalBody.appendChild(img);
            } else if (targetNode) {
                const clone = targetNode.cloneNode(true);
                modalBody.appendChild(clone);
            }
        }

        modalOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    };

    // Close Fullscreen Chart Modal
    window.closeChartFullscreen = function () {
        const modalOverlay = document.getElementById('chartFullscreenOverlay');
        if (modalOverlay) {
            modalOverlay.classList.remove('active');
            document.body.style.overflow = '';
        }
    };

    // Popout Chart in New Window / Popup
    window.popoutChart = function (elementOrId) {
        const { chartEl, title } = getChartContext(elementOrId);
        if (!chartEl) return;

        let imgUrl = '';
        if (chartEl.tagName === 'CANVAS') {
            imgUrl = chartEl.toDataURL('image/png');
        } else if (chartEl.tagName === 'IMG') {
            imgUrl = chartEl.src;
        }

        if (imgUrl) {
            const popWindow = window.open('', '_blank', 'width=950,height=650,resizable=yes');
            popWindow.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>${title} - Popout</title>
                    <style>
                        body { margin: 0; padding: 20px; background: #0f172a; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 90vh; font-family: sans-serif; color: white; }
                        h2 { margin-bottom: 20px; font-weight: 600; }
                        img { max-width: 95%; max-height: 80vh; border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); background: white; padding: 10px; }
                    </style>
                </head>
                <body>
                    <h2>${title}</h2>
                    <img src="${imgUrl}" alt="${title}">
                </body>
                </html>
            `);
            popWindow.document.close();
        } else {
            // Fallback to maximize modal if data URL not direct
            window.maximizeChart(elementOrId);
        }
    };

    // Download Chart as PNG
    window.downloadChartImage = function (elementOrId) {
        const { chartEl, title } = getChartContext(elementOrId);
        if (!chartEl) return;

        let dataUrl = '';
        if (chartEl.tagName === 'CANVAS') {
            dataUrl = chartEl.toDataURL('image/png');
        } else if (chartEl.tagName === 'IMG') {
            dataUrl = chartEl.src;
        }

        if (dataUrl) {
            const a = document.createElement('a');
            a.href = dataUrl;
            a.download = `${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_chart.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } else {
            alert('Chart image export is not supported for this element type.');
        }
    };

    // Toggle 3-dots Dropdown Menu
    window.toggleChartMenu = function (btn) {
        const dropdown = btn.parentElement.querySelector('.chart-menu-dropdown');
        if (!dropdown) return;

        // Close all other open dropdowns
        document.querySelectorAll('.chart-menu-dropdown').forEach(d => {
            if (d !== dropdown) {
                d.classList.remove('show');
                d.style.display = 'none';
            }
        });

        if (dropdown.classList.contains('show')) {
            dropdown.classList.remove('show');
            dropdown.style.display = 'none';
        } else {
            dropdown.classList.add('show');
            dropdown.style.display = 'flex';
        }
    };

    // Close menu dropdown when clicking outside
    document.addEventListener('click', function (e) {
        if (!e.target.closest('.chart-actions-toolbar')) {
            document.querySelectorAll('.chart-menu-dropdown').forEach(d => {
                d.classList.remove('show');
                d.style.display = 'none';
            });
        }
    });

    // Auto Helper Component Generator for Headers
    window.renderChartToolbarHTML = function (chartId) {
        const chartIdAttr = chartId ? `'${chartId}'` : 'this';
        return `
        <div class="chart-actions-toolbar">
            <button type="button" class="chart-btn chart-btn-popout" onclick="popoutChart(${chartIdAttr})" data-tooltip="Open in new window">
                <i class="fa-solid fa-arrow-up-right-from-square"></i>
            </button>
            <button type="button" class="chart-btn chart-btn-maximize" onclick="maximizeChart(${chartIdAttr})" data-tooltip="Maximize">
                <svg viewBox="0 0 24 24">
                    <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>
                </svg>
            </button>
            <button type="button" class="chart-btn chart-btn-options" onclick="toggleChartMenu(this)" data-tooltip="Options">
                <i class="fa-solid fa-ellipsis-vertical"></i>
            </button>
            <div class="chart-menu-dropdown" style="display: none;">
                <button type="button" class="chart-menu-item" onclick="maximizeChart(${chartIdAttr})">
                    <i class="fa-solid fa-expand me-1"></i> Fullscreen
                </button>
                <button type="button" class="chart-menu-item" onclick="downloadChartImage(${chartIdAttr})">
                    <i class="fa-solid fa-download me-1"></i> Download PNG
                </button>
                <button type="button" class="chart-menu-item" onclick="popoutChart(${chartIdAttr})">
                    <i class="fa-solid fa-external-link-alt me-1"></i> Popout Window
                </button>
            </div>
        </div>
        `;
    };

    // Initialize on DOM load
    document.addEventListener('DOMContentLoaded', function () {
        ensureFullscreenModal();
    });
})();
