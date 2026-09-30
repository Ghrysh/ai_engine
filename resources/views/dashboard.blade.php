@extends('layouts.app')

@section('content')
<div class="flex justify-between items-center mb-5">
    <h1 class="text-2xl font-normal text-[#c9d1d9]">Registered AI Engines</h1>
    <!-- Tombol Hijau khas GitHub Dark -->
    <button class="bg-[#238636] hover:bg-[#2ea043] text-white text-sm font-semibold py-1.5 px-3 border border-[rgba(240,246,252,0.1)] rounded-md shadow-sm transition-colors">
        <i class="fa-solid fa-plus mr-1"></i> New Engine
    </button>
</div>

<!-- Container Utama -->
<div class="bg-[#0d1117] border border-[#30363d] rounded-md overflow-hidden">
    
    <!-- Header Container -->
    <div class="bg-[#161b22] border-b border-[#30363d] px-4 py-3 text-sm font-semibold text-[#c9d1d9]">
        <i class="fa-solid fa-server mr-2 text-[#8b949e]"></i> Active Microservices
    </div>
    
    <ul class="divide-y divide-[#30363d]">
        
        <!-- List Item 1: Scraping Data -->
        <li class="p-4 flex items-center justify-between hover:bg-[#161b22] transition-colors">
            <div class="flex items-start">
                <i class="fa-solid fa-spider text-[#8b949e] mt-1 mr-3 text-base"></i>
                <div>
                    <!-- Link biru GitHub -->
                    <a href="#" class="text-[#58a6ff] font-semibold text-base hover:underline">Data Scraper Engine</a>
                    <p class="text-xs text-[#8b949e] mt-1.5">
                        Mengumpulkan sinyal sosial dari web. Endpoint: 
                        <code class="bg-[#30363d] text-[#c9d1d9] px-1.5 py-0.5 rounded text-[11px] font-mono tracking-wider">http://ews_ai_api:8000/scraping</code>
                    </p>
                </div>
            </div>
            <div class="flex flex-col items-end text-sm">
                <span class="px-2.5 py-0.5 border border-[#2ea043] text-[#3fb950] rounded-full text-xs font-medium mb-1.5 flex items-center">
                    <i class="fa-solid fa-circle text-[6px] mr-1.5"></i> Healthy
                </span>
                <span class="text-xs text-[#8b949e]">1,240 requests today</span>
            </div>
        </li>

        <!-- List Item 2: Analytics ML -->
        <li class="p-4 flex items-center justify-between hover:bg-[#161b22] transition-colors">
            <div class="flex items-start">
                <i class="fa-solid fa-chart-network text-[#8b949e] mt-1 mr-3 text-base"></i>
                <div>
                    <a href="#" class="text-[#58a6ff] font-semibold text-base hover:underline">EWS Big Data Analytics</a>
                    <p class="text-xs text-[#8b949e] mt-1.5">
                        KMeans, Random Forest & FP-Growth processing. Endpoint: 
                        <code class="bg-[#30363d] text-[#c9d1d9] px-1.5 py-0.5 rounded text-[11px] font-mono tracking-wider">http://ews_ai_api:8000/analytics/mining</code>
                    </p>
                </div>
            </div>
            <div class="flex flex-col items-end text-sm">
                <span class="px-2.5 py-0.5 border border-[#2ea043] text-[#3fb950] rounded-full text-xs font-medium mb-1.5 flex items-center">
                    <i class="fa-solid fa-circle text-[6px] mr-1.5"></i> Healthy
                </span>
                <span class="text-xs text-[#8b949e]">342 requests today</span>
            </div>
        </li>

        <!-- List Item 3: NLP Auto-Input -->
        <li class="p-4 flex items-center justify-between hover:bg-[#161b22] transition-colors">
            <div class="flex items-start">
                <i class="fa-solid fa-robot text-[#8b949e] mt-1 mr-3 text-base"></i>
                <div>
                    <a href="#" class="text-[#58a6ff] font-semibold text-base hover:underline">NLP Auto-Input Assistant</a>
                    <p class="text-xs text-[#8b949e] mt-1.5">
                        Memprediksi indikator konflik dari redaksi teks. Endpoint: 
                        <code class="bg-[#30363d] text-[#c9d1d9] px-1.5 py-0.5 rounded text-[11px] font-mono tracking-wider">http://ews_ai_api:8000/analyze</code>
                    </p>
                </div>
            </div>
            <div class="flex flex-col items-end text-sm">
                <!-- Badge Merah/Warning khas GitHub -->
                <span class="px-2.5 py-0.5 border border-[#f85149] text-[#f85149] rounded-full text-xs font-medium mb-1.5 flex items-center">
                    <i class="fa-solid fa-triangle-exclamation text-[8px] mr-1.5"></i> High Latency
                </span>
                <span class="text-xs text-[#8b949e]">8,912 requests today</span>
            </div>
        </li>
    </ul>
</div>
@endsection