<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Factory - Control Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #010409; }
        ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #484f58; }
        
        .modal-table-container { max-height: 60vh; overflow-y: auto; }
        .modal-table-head th { position: sticky; top: 0; z-index: 10; background-color: #161b22; color: #c9d1d9; cursor: pointer; }
        
        /* Transisi untuk efek minimize */
        #sidebar { transition: width 0.3s ease; }
        .sidebar-text { transition: opacity 0.2s ease; }
        .minimized .sidebar-text { display: none; }
        .minimized .menu-item { justify-content: center; padding-left: 0; padding-right: 0; }
        .minimized .menu-icon { margin-right: 0; font-size: 1.1rem; }
    </style>
</head>
<body class="antialiased h-screen flex flex-col overflow-hidden">

    <!-- Top Navbar -->
    <header class="bg-[#161b22] border-b border-[#30363d] px-4 py-3 flex items-center justify-between z-20 flex-shrink-0">
        <div class="flex items-center gap-4">
            <!-- Tombol Toggle Sidebar -->
            <button id="toggleSidebar" class="text-[#8b949e] hover:text-[#c9d1d9] focus:outline-none">
                <i class="fa-solid fa-bars text-lg"></i>
            </button>
            <div class="flex items-center gap-2">
                <i class="fa-solid fa-microchip text-[#c9d1d9] text-xl"></i>
                <span class="font-semibold text-sm tracking-wide text-[#c9d1d9]">AI ENGINE GATEWAY</span>
            </div>
        </div>
        <div>
            <form action="{{ route('logout') }}" method="POST">
                @csrf
                <button type="submit" class="text-sm text-[#8b949e] hover:text-[#f85149] transition-colors">
                    <i class="fa-solid fa-arrow-right-from-bracket mr-1"></i> Sign out
                </button>
            </form>
        </div>
    </header>

    <div class="flex flex-grow overflow-hidden">
        <!-- Sidebar -->
        <aside id="sidebar" class="w-64 bg-[#010409] border-r border-[#30363d] flex flex-col flex-shrink-0">
            <div class="p-3 overflow-y-auto flex-grow mt-2">
                
                <!-- Menu Utama -->
                <div class="mb-4">
                    <p class="sidebar-text text-[10px] font-semibold text-[#8b949e] mb-2 px-2 uppercase tracking-wider">Overview</p>
                    <a href="{{ route('dashboard') }}" class="menu-item flex items-center px-2 py-2 rounded-md text-sm mb-1 {{ request()->routeIs('dashboard') ? 'bg-[#1f6feb]/10 text-[#58a6ff]' : 'text-[#c9d1d9] hover:bg-[#161b22]' }}" title="Main Dashboard">
                        <i class="fa-solid fa-gauge-high w-6 text-center menu-icon"></i> 
                        <span class="sidebar-text">Main Dashboard</span>
                    </a>
                    <a href="{{ route('logs') }}" class="menu-item flex items-center px-2 py-2 rounded-md text-sm mb-1 {{ request()->routeIs('logs') ? 'bg-[#1f6feb]/10 text-[#58a6ff]' : 'text-[#c9d1d9] hover:bg-[#161b22]' }}" title="API Logs">
                        <i class="fa-solid fa-rectangle-list w-6 text-center menu-icon"></i> 
                        <span class="sidebar-text">Global API Logs</span>
                    </a>
                </div>

                <!-- List AI Engines -->
                <div>
                    <div class="flex items-center justify-between px-2 mb-2">
                        <p class="sidebar-text text-[10px] font-semibold text-[#8b949e] uppercase tracking-wider">Active Engines</p>
                        <a href="{{ route('engines.create') }}" class="sidebar-text text-[#8b949e] hover:text-[#c9d1d9]" title="Add New Engine"><i class="fa-solid fa-plus"></i></a>
                    </div>
                    
                    @php
                        $sidebarEngines = \App\Models\AiEngine::all();
                    @endphp

                    @foreach($sidebarEngines as $eng)
                    <a href="{{ route('engines.show', $eng->id) }}" class="menu-item flex items-center px-2 py-2 rounded-md text-sm mb-1 {{ request()->is('engines/'.$eng->id.'*') ? 'bg-[#161b22] text-[#c9d1d9] font-medium border-l-2 border-[#f78166]' : 'text-[#8b949e] hover:bg-[#161b22] hover:text-[#c9d1d9]' }}" title="{{ $eng->name }}">
                        <i class="fa-solid {{ str_contains(strtolower($eng->name), 'stream') ? 'fa-chart-pie' : (str_contains(strtolower($eng->name), 'scrape') ? 'fa-spider' : 'fa-robot') }} w-6 text-center menu-icon"></i> 
                        <span class="sidebar-text truncate flex-grow">{{ $eng->name }}</span>
                        @if($eng->is_active)
                            <i class="fa-solid fa-circle text-[6px] text-[#2ea043] sidebar-text ml-2 mt-1"></i>
                        @else
                            <i class="fa-solid fa-circle-notch text-[6px] text-[#8b949e] sidebar-text ml-2 mt-1"></i>
                        @endif
                    </a>
                    @endforeach
                </div>
            </div>
        </aside>

        <!-- Main Content (Scrollable) -->
        <main class="flex-grow overflow-y-auto bg-[#0d1117] p-6 relative">
            <div class="max-w-7xl w-full mx-auto">
                @if(session('success'))
                    <div class="mb-5 bg-[#238636]/10 border border-[#2ea043]/30 text-[#3fb950] px-4 py-3 rounded-md text-sm flex items-center gap-2">
                        <i class="fa-solid fa-circle-check"></i> {{ session('success') }}
                    </div>
                @endif
                @yield('content')
            </div>
        </main>
    </div>

    <!-- Script Minimize Sidebar -->
    <script>
        document.getElementById('toggleSidebar').addEventListener('click', function() {
            const sidebar = document.getElementById('sidebar');
            if (sidebar.classList.contains('w-64')) {
                sidebar.classList.remove('w-64');
                sidebar.classList.add('w-16', 'minimized');
            } else {
                sidebar.classList.remove('w-16', 'minimized');
                sidebar.classList.add('w-64');
            }
        });
    </script>
</body>
</html>