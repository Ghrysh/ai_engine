@extends('layouts.app')

@section('content')
<div class="flex justify-between items-start mb-6">
    <div>
        <h1 class="text-2xl font-normal text-[#c9d1d9] flex items-center gap-3">
            {{ $engine->name }}
            @if($engine->is_active)
                <span class="px-2 py-0.5 border border-[#2ea043] text-[#3fb950] rounded-full text-xs font-medium">Active</span>
            @else
                <span class="px-2 py-0.5 border border-[#30363d] text-[#8b949e] rounded-full text-xs font-medium">Disabled</span>
            @endif
        </h1>
        <p class="text-sm text-[#8b949e] mt-1"><i class="fa-solid fa-server mr-1"></i> Origin Target: {{ $engine->base_url }}</p>
    </div>
</div>

<!-- API Kredensial Box -->
<div class="bg-[#0d1117] border border-[#30363d] rounded-md mb-6 p-4">
    <h3 class="text-sm font-semibold text-[#c9d1d9] mb-3"><i class="fa-solid fa-key text-[#8b949e] mr-2"></i> API Credentials</h3>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Endpoint URL -->
        <div>
            <label class="block text-xs font-medium text-[#8b949e] mb-1">Gateway API Endpoint</label>
            <div class="flex items-center">
                <input type="text" readonly value="{{ url('/api/v1/engine/'.$engine->id) }}" id="apiUrl" class="w-full bg-[#010409] border border-[#30363d] rounded-l-md px-3 py-1.5 text-sm text-[#c9d1d9] font-mono focus:outline-none">
                <button onclick="copyToClipboard('apiUrl')" class="bg-[#21262d] border-y border-r border-[#30363d] hover:bg-[#30363d] px-3 py-1.5 rounded-r-md text-[#c9d1d9] transition-colors" title="Copy URL">
                    <i class="fa-regular fa-copy"></i>
                </button>
            </div>
            <p class="text-[11px] text-[#8b949e] mt-1">Tambahkan endpoint spesifik (misal: <code>/analyze</code>) di akhir URL ini pada project klien Anda.</p>
        </div>

        <!-- API Key -->
        <div>
            <label class="block text-xs font-medium text-[#8b949e] mb-1">Bearer API Key</label>
            <div class="flex items-center gap-2">
                <div class="flex items-center w-full">
                    <input type="password" readonly value="{{ $engine->api_key }}" id="apiKey" class="w-full bg-[#010409] border border-[#30363d] rounded-l-md px-3 py-1.5 text-sm text-[#c9d1d9] font-mono focus:outline-none">
                    <button onclick="toggleVisibility('apiKey')" class="bg-[#21262d] border-y border-[#30363d] hover:bg-[#30363d] px-3 py-1.5 text-[#c9d1d9] transition-colors" title="Show Key">
                        <i class="fa-regular fa-eye"></i>
                    </button>
                    <button onclick="copyToClipboard('apiKey')" class="bg-[#21262d] border-y border-r border-[#30363d] hover:bg-[#30363d] px-3 py-1.5 rounded-r-md text-[#c9d1d9] transition-colors" title="Copy Key">
                        <i class="fa-regular fa-copy"></i>
                    </button>
                </div>
                <!-- Tombol Revoke/Regenerate -->
                <form action="{{ route('engines.generate-key', $engine->id) }}" method="POST" onsubmit="return confirm('Yakin ingin membuat API Key baru? Key lama tidak akan bisa digunakan lagi oleh aplikasi klien!');">
                    @csrf
                    <button type="submit" class="bg-[#21262d] border border-[#30363d] hover:border-[#f85149] hover:text-[#f85149] px-3 py-1.5 rounded-md text-[#c9d1d9] text-sm font-semibold transition-colors">
                        Regenerate
                    </button>
                </form>
            </div>
        </div>
    </div>
</div>

<!-- ============================================== -->
<!-- UI STREAMLIT DASHBOARD (Jika Type = Dashboard) -->
<!-- ============================================== -->
@if(str_contains(strtolower($engine->name), 'stream') || str_contains(strtolower($engine->name), 'dashboard') || str_contains(strtolower($engine->name), 'scraper') || $engine->type == 'Dashboard')
    <div class="bg-[#0d1117] border border-[#30363d] rounded-md overflow-hidden">
        <div class="bg-[#161b22] border-b border-[#30363d] px-4 py-3 text-sm font-semibold text-[#c9d1d9] flex justify-between items-center">
            <span><i class="fa-solid fa-desktop text-[#8b949e] mr-2"></i> Streamlit Application Interface</span>
            <a href="{{ $engine->base_url }}" target="_blank" class="text-xs text-[#58a6ff] hover:underline">Buka di Tab Baru <i class="fa-solid fa-external-link text-[10px]"></i></a>
        </div>
        <!-- Iframe ke Streamlit -->
        <iframe src="{{ $engine->base_url }}" width="100%" height="800px" frameborder="0" class="w-full"></iframe>
    </div>

<!-- ============================================== -->
<!-- UI DATA MINING ANALYTICS (ApexCharts)          -->
<!-- ============================================== -->
@elseif(str_contains(strtolower($engine->name), 'analytic') || $engine->type == 'Analytics')
    <div class="bg-[#0d1117] border border-[#30363d] rounded-md overflow-hidden p-4">
        <div class="flex justify-between items-center mb-4">
            <div>
                <h2 class="text-lg font-semibold text-[#c9d1d9]"><i class="fa-solid fa-brain text-[#8b949e] mr-2"></i> Data Mining Visualizations</h2>
                <p class="text-xs text-[#8b949e] mt-1"><i class="fa-solid fa-info-circle mr-1"></i> Data analitik ditarik langsung dari model AI via API Gateway.</p>
            </div>
            <button id="btn-refresh-ai" class="text-xs bg-[#21262d] border border-[#30363d] px-3 py-1.5 rounded-md text-[#c9d1d9] hover:bg-[#30363d] transition-colors"><i class="fa-solid fa-sync-alt mr-1"></i> Refresh Data</button>
        </div>

        <!-- Indikator Loading -->
        <div id="loading-indicator" class="text-center py-10" style="display: none;">
            <i class="fa-solid fa-circle-notch fa-spin text-[#58a6ff] text-3xl mb-3"></i>
            <p class="text-sm text-[#8b949e]">Processing Data Mining Algorithms (KMeans, FP-Growth, Decision Tree)...</p>
        </div>

        <div id="analytics-container" class="grid grid-cols-1 md:grid-cols-2 gap-4" style="display: none;">
            @php
            $chartConfig = [1=>6, 2=>6, 3=>12, 4=>6, 5=>6, 6=>12, 7=>6, 8=>6, 9=>12, 10=>12];
            @endphp

            @foreach($chartConfig as $i =>$size)
            <div class="{{ $size == 12 ? 'col-span-1 md:col-span-2' : 'col-span-1' }}">
                <div class="bg-[#010409] border border-[#30363d] hover:border-[#8b949e] transition-colors rounded-md h-full flex flex-col p-3 shadow-sm">
                    <div class="flex justify-between items-start mb-2 border-b border-[#30363d] pb-2">
                        <h3 class="text-sm font-semibold text-[#c9d1d9]" id="title-q{{$i}}">{{$i}}. Memuat...</h3>
                        <span class="text-[10px] bg-[#161b22] px-2 py-0.5 rounded border border-[#30363d] text-[#8b949e]" id="badge-q{{$i}}">ML</span>
                    </div>
                    <div id="chart-q{{$i}}" class="flex-grow w-full" style="min-height: 280px;"></div>
                    
                    <div id="ai-narrative-q{{$i}}" class="hidden mt-3 p-3 bg-[#161b22] border border-[#30363d] rounded flex flex-col gap-3">
                        <div class="text-xs text-[#c9d1d9] leading-relaxed">
                            <i class="fa-solid fa-robot text-[#58a6ff] mr-1"></i> <span id="ai-text-q{{$i}}"></span>
                        </div>
                        <div class="text-right border-t border-[#30363d] pt-2">
                            <button onclick="openDetailModal('q{{$i}}')" class="text-[10px] bg-[#21262d] border border-[#30363d] px-2 py-1.5 rounded text-[#58a6ff] hover:bg-[#30363d] hover:text-white transition-colors">
                                <i class="fa-solid fa-search-plus mr-1"></i> Detail Analitik
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            @endforeach
        </div>
    </div>

    <!-- TAILWIND MODAL DRILL DOWN DETAILS -->
    <div id="drillDownModal" class="fixed inset-0 z-50 hidden overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
        <!-- Background backdrop -->
        <div class="fixed inset-0 bg-[#010409] bg-opacity-80 transition-opacity" onclick="closeDetailModal()"></div>

        <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
            <div class="relative transform overflow-hidden rounded-lg bg-[#0d1117] border border-[#30363d] text-left shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-5xl">
                <!-- Modal Header -->
                <div class="bg-[#161b22] border-b border-[#30363d] px-4 py-3 flex justify-between items-center">
                    <h3 class="text-sm font-semibold text-[#c9d1d9]" id="drillDownModalLabel">
                        <i class="fa-solid fa-table mr-2 text-[#8b949e]"></i> Detail Data Mining
                    </h3>
                    <button type="button" class="text-[#8b949e] hover:text-[#f85149] transition-colors" onclick="closeDetailModal()">
                        <i class="fa-solid fa-xmark text-lg"></i>
                    </button>
                </div>
                
                <!-- AI Narrative in Modal -->
                <div class="bg-[#010409] border-b border-[#30363d] p-4 text-xs text-[#58a6ff] leading-relaxed hidden" id="modal-ai-narrative"></div>
                
                <!-- Modal Body (Table) -->
                <div class="max-h-[60vh] overflow-y-auto p-0">
                    <table class="w-full text-left border-collapse text-xs text-[#c9d1d9]" id="detail-table">
                        <thead class="bg-[#161b22] text-[#8b949e] sticky top-0 shadow-sm z-10 border-b border-[#30363d]">
                            <tr id="modal-table-head"></tr>
                        </thead>
                        <tbody id="modal-table-body" class="divide-y divide-[#30363d]"></tbody>
                    </table>
                </div>
                
                <!-- Modal Footer -->
                <div class="bg-[#161b22] border-t border-[#30363d] px-4 py-3 sm:flex sm:flex-row-reverse">
                    <button type="button" class="bg-[#21262d] border border-[#30363d] hover:bg-[#30363d] px-4 py-1.5 rounded-md text-[#c9d1d9] text-xs font-semibold transition-colors" onclick="closeDetailModal()">Tutup</button>
                </div>
            </div>
        </div>
    </div>

<!-- ============================================== -->
<!-- UI NLP AUTO-INPUT ASSISTANT                    -->
<!-- ============================================== -->
@elseif(str_contains(strtolower($engine->name), 'nlp') || str_contains(strtolower($engine->name), 'assistant') || $engine->type == 'NLP')
    <div class="bg-[#0d1117] border border-[#30363d] rounded-md overflow-hidden p-4">
        <div class="flex justify-between items-center mb-4">
            <div>
                <h2 class="text-lg font-semibold text-[#c9d1d9]">
                    <i class="fa-solid fa-robot text-[#3fb950] mr-2"></i> NLP Auto-Input Assistant
                </h2>
                <p class="text-xs text-[#8b949e] mt-1">
                    <i class="fa-solid fa-info-circle mr-1"></i> Uji coba ekstraksi teks kronologi konflik menggunakan model NLP FastAPI via API Gateway.
                </p>
            </div>
            <span class="text-[10px] bg-[#3fb950]/20 text-[#3fb950] px-2 py-0.5 rounded border border-[#3fb950]/30 font-medium">AI Powered</span>
        </div>

        <!-- Input Form (GitHub Box Style) -->
        <div class="bg-[#010409] border border-[#30363d] rounded-md p-4 mb-4">
            <label for="kronologiInput" class="block text-xs font-medium text-[#8b949e] mb-2">Deskripsi / Kronologi Kejadian</label>
            <textarea id="kronologiInput" rows="4" 
                class="w-full bg-[#0d1117] border border-[#30363d] rounded-md p-3 text-sm text-[#c9d1d9] focus:outline-none focus:border-[#58a6ff]" 
                placeholder="Masukkan teks kronologi konflik secara detail (minimal 10 karakter)..."></textarea>
            
            <button type="button" id="btnAnalyzeAI" 
                class="mt-3 bg-[#2ea44f] hover:bg-[#2c974b] text-white px-4 py-2 rounded-md text-xs font-semibold transition-colors flex items-center gap-2">
                <i class="fa-solid fa-wand-magic-sparkles"></i> Analisis dengan AI Engine
            </button>
        </div>

        <!-- Hasil Ekstraksi (Result Callout Box) -->
        <div id="nlpResultContainer" class="bg-[#010409] border border-[#30363d] rounded-md p-4 hidden border-l-4 border-l-[#2ea44f]">
            <h3 class="text-sm font-semibold text-[#c9d1d9] mb-3">
                <i class="fa-solid fa-check-circle text-[#3fb950] mr-2"></i> Hasil Ekstraksi NLP AI:
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-[#c9d1d9]">
                <div>
                    <strong>Tingkat Relevansi (Skor):</strong> 
                    <span id="resScore" class="px-2 py-0.5 border border-[#2ea043] text-[#3fb950] bg-[#2ea043]/10 rounded-full font-mono"></span>
                </div>
                <div>
                    <strong>Dimensi Konflik:</strong> 
                    <span id="resDimensi" class="text-[#58a6ff]"></span>
                </div>
                <div>
                    <strong>Sub Dimensi:</strong> 
                    <span id="resSubDimensi" class="text-[#58a6ff]"></span>
                </div>
                <div>
                    <strong>Indikator Isu:</strong> 
                    <span id="resIndikator" class="text-[#58a6ff] font-semibold"></span>
                </div>
                <div class="col-span-1 md:col-span-2">
                    <strong>Fase Konflik:</strong> 
                    <span id="resFase" class="px-2 py-0.5 border border-[#f85149] text-[#f85149] bg-[#f85149]/10 rounded-full font-medium"></span>
                </div>
                <div class="col-span-1 md:col-span-2 mt-2">
                    <div class="bg-[#0d1117] border border-[#30363d] rounded-md p-3">
                        <strong class="text-[10px] text-[#8b949e] uppercase block mb-1">Rekomendasi Cegah Dini:</strong>
                        <span id="resRekomendasi" class="text-[#8b949e] leading-relaxed"></span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Script AJAX untuk Handler NLP Assistant -->
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        const btn = document.getElementById('btnAnalyzeAI');
        if(btn) {
            btn.addEventListener('click', async function() {
                let kronologi = document.getElementById('kronologiInput').value;
                if(kronologi.length < 10) {
                    alert('Kronologi terlalu singkat. Minimal masukkan 10 karakter.');
                    return;
                }

                let originalHTML = btn.innerHTML;
                btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1"></i> Menganalisis...`;
                btn.disabled = true;

                try {
                    // Menggunakan endpoint API Gateway Laravel yang otomatis meneruskan ke FastAPI (/analyze)
                    let response = await fetch('{{ url('/api/v1/engine/'.$engine->id.'/analyze') }}', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                            'Authorization': 'Bearer {{ $engine->api_key }}'
                        },
                        body: JSON.stringify({ text: kronologi })
                    });
                    let res = await response.json();

                    if(response.ok) {
                        document.getElementById('resScore').innerText = (res.score * 100).toFixed(1) + '%';
                        document.getElementById('resDimensi').innerText = res.dimensi;
                        document.getElementById('resSubDimensi').innerText = res.sub_dimensi;
                        document.getElementById('resIndikator').innerText = res.indikator;
                        document.getElementById('resFase').innerText = res.fase;
                        document.getElementById('resRekomendasi').innerText = res.rekomendasi;
                        document.getElementById('nlpResultContainer').classList.remove('hidden');
                    } else {
                        alert('Gagal memproses AI: ' + (res.message || 'Terjadi kesalahan pada server.'));
                    }
                } catch(err) {
                    alert('Error koneksi ke API Gateway: ' + err.message);
                } finally {
                    btn.innerHTML = originalHTML;
                    btn.disabled = false;
                }
            });
        }
    });
    </script>
@endif

<script>
    function copyToClipboard(elementId) {
        var copyText = document.getElementById(elementId);
        copyText.select();
        copyText.setSelectionRange(0, 99999);
        navigator.clipboard.writeText(copyText.value);
        alert("Disalin: " + copyText.value);
    }

    function toggleVisibility(elementId) {
        var input = document.getElementById(elementId);
        input.type = input.type === "password" ? "text" : "password";
    }
</script>

<!-- SCRIPTS KHUSUS JIKA ENGINE ADALAH ANALYTICS -->
@if(str_contains(strtolower($engine->name), 'analytic') || $engine->type == 'Analytics')
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<script>
    let chartsInstance = {}; 
    let miningData = {}; // Cache data dari API untuk modal

    // --- FUNGSI MODAL ---
    window.openDetailModal = function(qKey) {
        const data = miningData[qKey];
        if(!data) return;

        document.getElementById('drillDownModalLabel').innerHTML = `<i class="fa-solid fa-database mr-2 text-[#8b949e]"></i> ${data.title}`;
        const modalNarasi = document.getElementById('modal-ai-narrative');
        
        if(data.detail_data && data.detail_data.ai_detail_narrative) {
            modalNarasi.innerHTML = `<i class="fa-solid fa-robot mr-2"></i> <strong class="text-[#c9d1d9]">Insight AI:</strong> ${data.detail_data.ai_detail_narrative}`;
            modalNarasi.classList.remove('hidden');
        } else {
            modalNarasi.classList.add('hidden');
        }

        const thead = document.getElementById('modal-table-head');
        const tbody = document.getElementById('modal-table-body');
        thead.innerHTML = ''; tbody.innerHTML = '';
        
        if (!data.detail_data || !data.detail_data.headers || data.detail_data.rows.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" class="text-center py-6 text-[#8b949e]">Data detail tidak tersedia.</td></tr>';
            document.getElementById('drillDownModal').classList.remove('hidden'); 
            return;
        }

        // Generate Headers
        data.detail_data.headers.forEach((h, index) => { 
            let th = document.createElement('th');
            th.className = 'px-4 py-3 font-semibold cursor-pointer hover:bg-[#30363d] select-none group transition-colors';
            th.innerHTML = `${h} <span class="opacity-30 text-[10px] ml-1 group-hover:opacity-100 transition-opacity">&#x21C5;</span>`;
            th.onclick = function() { sortTable(index); };
            thead.appendChild(th);
        });

        // Generate Rows
        data.detail_data.rows.forEach(rowArray => {
            let tr = document.createElement('tr');
            tr.className = 'hover:bg-[#161b22] transition-colors';
            
            rowArray.forEach(cellText => {
                let textLower = cellText ? cellText.toString().toLowerCase() : '';
                let badgeClass = '';
                
                // Logika pewarnaan badge ala Tailwind (GitHub Dark Mode Style)
                if (textLower === '✓ tepat' || textLower === '✓ benar') badgeClass = 'border border-[#2ea043] text-[#3fb950] bg-[#2ea043]/10 px-2 py-0.5 rounded-full text-[10px] font-medium';
                else if (textLower === '✗ meleset' || textLower === '✗ salah') badgeClass = 'border border-[#f85149] text-[#f85149] bg-[#f85149]/10 px-2 py-0.5 rounded-full text-[10px] font-medium';
                else if (textLower.includes('fase ')) badgeClass = 'border border-[#d29922] text-[#d29922] bg-[#d29922]/10 px-2 py-0.5 rounded-full text-[10px] font-medium';
                else if (textLower.includes('selesai') || textLower.includes('closed') || textLower === 'ya') badgeClass = 'border border-[#2ea043] text-[#3fb950] bg-[#2ea043]/10 px-2 py-0.5 rounded-full text-[10px] font-medium';
                else if (textLower.includes('open') || textLower.includes('draft') || textLower === 'tidak') badgeClass = 'border border-[#f85149] text-[#f85149] bg-[#f85149]/10 px-2 py-0.5 rounded-full text-[10px] font-medium';
                
                let td = document.createElement('td');
                td.className = 'px-4 py-3 whitespace-nowrap';
                
                if (badgeClass) {
                    td.innerHTML = `<span class="${badgeClass}">${cellText}</span>`;
                } else if (textLower.includes('[bobot')) {
                    td.innerHTML = `<span class="font-semibold text-[#58a6ff]"><i class="fa-solid fa-star mr-1"></i> Variabel Penting</span>`;
                } else if (!isNaN(cellText) && cellText.toString().trim() !== '' && !textLower.includes('hari')) {
                    td.classList.add('font-semibold', 'text-[#58a6ff]');
                    td.innerText = cellText;
                } else {
                    td.innerText = cellText;
                }
                
                td.setAttribute('data-sort', cellText);
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        
        document.getElementById('drillDownModal').classList.remove('hidden');
    };

    window.closeDetailModal = function() {
        document.getElementById('drillDownModal').classList.add('hidden');
    };

    // Fungsi Sorting Kolom Table
    function sortTable(n) {
        let table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
        table = document.getElementById("detail-table");
        switching = true;
        dir = "asc"; 
        
        while (switching) {
            switching = false;
            rows = table.rows;
            for (i = 1; i < (rows.length - 1); i++) {
                shouldSwitch = false;
                x = rows[i].getElementsByTagName("TD")[n];
                y = rows[i + 1].getElementsByTagName("TD")[n];
                
                let valX = x.getAttribute('data-sort').toLowerCase();
                let valY = y.getAttribute('data-sort').toLowerCase();
                
                let numX = parseFloat(valX.replace(/[^\d.-]/g, ''));
                let numY = parseFloat(valY.replace(/[^\d.-]/g, ''));
                let isNumeric = !isNaN(numX) && !isNaN(numY) && valX.match(/\d/) && valY.match(/\d/);

                if (dir == "asc") {
                    if (isNumeric ? numX > numY : valX > valY) {
                        shouldSwitch = true;
                        break;
                    }
                } else if (dir == "desc") {
                    if (isNumeric ? numX < numY : valX < valY) {
                        shouldSwitch = true;
                        break;
                    }
                }
            }
            if (shouldSwitch) {
                rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                switching = true;
                switchcount ++; 
            } else {
                if (switchcount == 0 && dir == "asc") {
                    dir = "desc";
                    switching = true;
                }
            }
        }
    }

    // --- FUNGSI APEXCHARTS ---
    document.addEventListener('DOMContentLoaded', function() {
        const btnRefresh = document.getElementById('btn-refresh-ai');
        
        const getApexType = (chart_type) => {
            if (chart_type === 'horizontal_bar' || chart_type === 'grouped_bar' || chart_type === 'stacked_bar') return 'bar';
            return chart_type;
        };

        async function loadAiAnalytics() {
            document.getElementById('analytics-container').style.display = 'none';
            document.getElementById('loading-indicator').style.display = 'block';
            
            try {
                const response = await fetch('{{ url('/api/v1/engine/'.$engine->id.'/analytics/mining') }}', { 
                    method: 'GET', 
                    headers: { 
                        'Accept': 'application/json',
                        'Authorization': 'Bearer {{ $engine->api_key }}'
                    }
                });
                
                const res = await response.json();

                if (res.status === 'success' && res.charts) {
                    miningData = res.charts; // Simpan ke global cache untuk Modal

                    for (let i = 1; i <= 10; i++) {
                        let qKey = 'q' + i;
                        let data = res.charts[qKey];
                        if (!data || !data.chart_config) continue;

                        document.getElementById(`title-${qKey}`).innerText = `${i}. ${data.title}`;
                        
                        // Badge text & color logic (Tailwind equivalents)
                        let badge = document.getElementById(`badge-${qKey}`);
                        badge.innerText = data.technique;
                        if(data.technique.includes('Clustering')) badge.className = 'text-[10px] bg-[#3498db]/20 text-[#3498db] px-2 py-0.5 rounded border border-[#3498db]/30';
                        else if(data.technique.includes('Association')) badge.className = 'text-[10px] bg-[#3fb950]/20 text-[#3fb950] px-2 py-0.5 rounded border border-[#3fb950]/30';
                        else if(data.technique.includes('Predictive')) badge.className = 'text-[10px] bg-[#f85149]/20 text-[#f85149] px-2 py-0.5 rounded border border-[#f85149]/30';
                        else badge.className = 'text-[10px] bg-[#d29922]/20 text-[#d29922] px-2 py-0.5 rounded border border-[#d29922]/30';

                        document.getElementById(`ai-text-${qKey}`).innerText = data.ai_narrative;
                        document.getElementById(`ai-narrative-${qKey}`).classList.remove('hidden');

                        let options = {
                            series: data.chart_config.series || [],
                            theme: { mode: 'dark' },
                            chart: {
                                type: getApexType(data.chart_type),
                                height: 320, background: 'transparent',
                                toolbar: { show: true, tools: { download: true, selection: true, zoom: true, pan: true, reset: true } },
                                zoom: { enabled: true, type: 'x' },
                                animations: { enabled: true }
                            },
                            colors: ['#58a6ff', '#3fb950', '#f85149', '#d29922', '#a371f7'],
                            dataLabels: { enabled: false },
                            stroke: { curve: 'smooth', width: data.chart_type === 'line' || data.chart_type === 'radar' ? 2 : 0 },
                            legend: { position: 'bottom', labels: { colors: '#c9d1d9' } },
                            xaxis: { labels: { style: { colors: '#8b949e' } } },
                            yaxis: { labels: { style: { colors: '#8b949e' } } }
                        };

                        if (data.chart_type === 'stacked_bar') { options.chart.stacked = true; options.xaxis.categories = data.chart_config.categories; } 
                        else if (data.chart_type === 'horizontal_bar') { options.plotOptions = { bar: { horizontal: true, borderRadius: 2 } }; options.xaxis.categories = data.chart_config.categories; options.chart.zoom.type = 'y'; }
                        else if (data.chart_type === 'bar' || data.chart_type === 'grouped_bar') { options.plotOptions = { bar: { borderRadius: 2 } }; options.xaxis.categories = data.chart_config.categories; }
                        else if (data.chart_type === 'line' || data.chart_type === 'radar') { options.xaxis.categories = data.chart_config.categories; }
                        else if (data.chart_type === 'heatmap') { options.plotOptions = { heatmap: { shadeIntensity: 0.5, radius: 2, useFillColorAsStroke: false } }; options.dataLabels = { enabled: true, style: { colors: ['#fff'] } }; options.colors = ['#58a6ff']; options.chart.zoom.type = 'xy'; }
                        else if (data.chart_type === 'scatter') { options.xaxis.type = 'numeric'; options.yaxis.type = 'numeric'; options.chart.zoom.type = 'xy'; }
                        else if (data.chart_type === 'bubble') { options.xaxis.type = 'numeric'; options.yaxis.type = 'numeric'; options.dataLabels = { enabled: false }; options.chart.zoom.type = 'xy'; }
                        else if (data.chart_type === 'radialBar') { options.plotOptions = { radialBar: { hollow: { size: '65%' }, dataLabels: { value: { color: '#f85149', formatter: val => val + "%" } } } }; options.labels = data.chart_config.labels || ['Akurasi']; options.chart.zoom.enabled = false; }
                        
                        const chartDiv = document.querySelector(`#chart-${qKey}`);
                        if (chartDiv) {
                            if (chartsInstance[qKey]) chartsInstance[qKey].destroy();
                            chartDiv.innerHTML = '';
                            const chart = new ApexCharts(chartDiv, options);
                            chart.render();
                            chartsInstance[qKey] = chart;
                        }
                    }
                    document.getElementById('loading-indicator').style.display = 'none';
                    document.getElementById('analytics-container').style.display = 'grid';
                }
            } catch (error) {
                document.getElementById('loading-indicator').style.display = 'none';
                alert('Gagal mengambil data dari AI Gateway: ' + error.message);
            }
        }

        btnRefresh.addEventListener('click', () => loadAiAnalytics());
        loadAiAnalytics();
    });
</script>
@endif
@endsection