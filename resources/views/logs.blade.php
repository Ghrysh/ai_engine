@extends('layouts.app')

@section('content')
<div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-5 gap-3">
    <h1 class="text-2xl font-normal text-[#c9d1d9]">API Request Logs</h1>
    
    <!-- Perbaikan: Gunakan route('logs') alih-alih route('logs.index') -->
    <form method="GET" action="{{ route('logs') }}" class="flex items-center gap-2">
        <select name="engine_id" onchange="this.form.submit()" class="bg-[#0d1117] border border-[#30363d] rounded-md px-3 py-1.5 text-sm text-[#c9d1d9] focus:outline-none focus:border-[#58a6ff]">
            <option value="">Semua AI Engine</option>
            @foreach($engines as $engine)
                <option value="{{ $engine->id }}" {{ request('engine_id') == $engine->id ? 'selected' : '' }}>
                    {{ $engine->name }}
                </option>
            @endforeach
        </select>
        
        @if(request('engine_id'))
            <a href="{{ route('logs') }}" class="text-xs bg-[#21262d] border border-[#30363d] hover:bg-[#30363d] px-3 py-1.5 rounded-md text-[#c9d1d9] transition-colors flex items-center">
                Reset
            </a>
        @endif
    </form>
</div>

<div class="bg-[#0d1117] border border-[#30363d] rounded-md overflow-hidden">
    <div class="bg-[#161b22] border-b border-[#30363d] px-4 py-3 text-sm font-semibold text-[#c9d1d9]">
        <i class="fa-solid fa-list-ul mr-2 text-[#8b949e]"></i> Recent Activity 
        @if(request('engine_id'))
            <span class="text-xs text-[#58a6ff] font-normal ml-2">(Difilter berdasarkan Engine terpilih)</span>
        @endif
    </div>
    
    <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-[#161b22] border-b border-[#30363d] text-[#8b949e] text-xs uppercase tracking-wider">
                    <th class="px-4 py-3 font-semibold">Timestamp</th>
                    <th class="px-4 py-3 font-semibold">Engine</th>
                    <th class="px-4 py-3 font-semibold">Endpoint</th>
                    <th class="px-4 py-3 font-semibold">Status</th>
                    <th class="px-4 py-3 font-semibold">Latency</th>
                    <th class="px-4 py-3 font-semibold">Client IP</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-[#30363d] text-sm text-[#c9d1d9]">
                @forelse($logs as $log)
                <tr class="hover:bg-[#161b22] transition-colors">
                    <td class="px-4 py-3 whitespace-nowrap text-[#8b949e]">{{ $log->created_at->format('d M Y, H:i:s') }}</td>
                    <td class="px-4 py-3 font-medium text-[#58a6ff]">{{ $log->engine->name ?? 'Unknown' }}</td>
                    <td class="px-4 py-3">
                        <code class="bg-[#30363d] px-1.5 py-0.5 rounded text-[11px] font-mono tracking-wider text-[#c9d1d9]">
                            /{{ $log->endpoint_accessed }}
                        </code>
                    </td>
                    <td class="px-4 py-3">
                        @if($log->status_code >= 200 && $log->status_code < 300)
                            <span class="px-2 py-0.5 border border-[#2ea043] text-[#3fb950] rounded-full text-xs font-medium">
                                {{ $log->status_code }} OK
                            </span>
                        @else
                            <span class="px-2 py-0.5 border border-[#f85149] text-[#f85149] rounded-full text-xs font-medium">
                                {{ $log->status_code }} Error
                            </span>
                        @endif
                    </td>
                    <td class="px-4 py-3">
                        <span class="{{ $log->response_time_ms > 1000 ? 'text-[#d29922]' : 'text-[#8b949e]' }}">
                            {{ number_format($log->response_time_ms, 2) }} ms
                        </span>
                    </td>
                    <td class="px-4 py-3 text-[#8b949e]">{{ $log->client_ip }}</td>
                </tr>
                @empty
                <tr>
                    <td colspan="6" class="px-4 py-8 text-center text-[#8b949e]">Belum ada data log API untuk filter ini.</td>
                </tr>
                @endforelse
            </tbody>
        </table>
    </div>
    
    <!-- Pagination Component -->
    @if($logs->hasPages())
    <div class="px-4 py-3 border-t border-[#30363d] bg-[#0d1117]">
        {{ $logs->appends(request()->query())->links('pagination::tailwind') }}
    </div>
    @endif
</div>
@endsection