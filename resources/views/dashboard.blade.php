@extends('layouts.app')

@section('content')
<div class="flex justify-between items-center mb-5">
    <h1 class="text-2xl font-normal text-[#c9d1d9]">Registered AI Engines</h1>
    <!-- Tombol Hijau khas GitHub Dark -->
    <a href="{{ route('engines.create') }}" class="bg-[#238636] hover:bg-[#2ea043] text-white text-sm font-semibold py-1.5 px-3 border border-[rgba(240,246,252,0.1)] rounded-md shadow-sm transition-colors">
        <i class="fa-solid fa-plus mr-1"></i> New Engine
    </a>
</div>

<!-- Container Utama -->
<div class="bg-[#0d1117] border border-[#30363d] rounded-md overflow-hidden">
    
    <!-- Header Container -->
    <div class="bg-[#161b22] border-b border-[#30363d] px-4 py-3 text-sm font-semibold text-[#c9d1d9]">
        <i class="fa-solid fa-server mr-2 text-[#8b949e]"></i> Active Microservices
    </div>
    
    <ul class="divide-y divide-[#30363d]">
        @forelse ($engines as $engine)
            <li class="p-4 flex flex-col md:flex-row md:items-center justify-between hover:bg-[#161b22] transition-colors gap-4">
                <div class="flex items-start">
                    <div>
                        <a href="{{ route('engines.show', $engine->id) }}" class="text-[#58a6ff] font-semibold text-base hover:underline">{{ $engine->name }}</a>
                        <p class="text-xs text-[#8b949e] mt-1.5 flex items-center gap-2">
                            <span class="px-1.5 py-0.5 rounded bg-[#30363d] text-[#c9d1d9] text-[10px] uppercase font-bold">{{ $engine->type }}</span>
                            Target URL: 
                            <code class="text-[#c9d1d9] text-[11px] font-mono tracking-wider">{{ $engine->base_url }}</code>
                        </p>
                    </div>
                </div>
                <div class="flex flex-col md:items-end text-sm gap-2">
                    <div class="flex items-center gap-2">
                        @if($engine->is_active)
                            <span class="px-2.5 py-0.5 border border-[#2ea043] text-[#3fb950] rounded-full text-xs font-medium inline-flex items-center">
                                <i class="fa-solid fa-circle text-[6px] mr-1.5"></i> Active
                            </span>
                        @else
                            <span class="px-2.5 py-0.5 border border-[#30363d] text-[#8b949e] rounded-full text-xs font-medium inline-flex items-center">
                                <i class="fa-solid fa-circle text-[6px] mr-1.5"></i> Disabled
                            </span>
                        @endif
                        <a href="{{ route('engines.edit', $engine->id) }}" class="px-2.5 py-1 bg-[#21262d] hover:bg-[#30363d] border border-[#30363d] rounded-md text-xs font-medium text-[#c9d1d9] transition-colors" title="Edit Engine">
                            <i class="fa-solid fa-pen"></i>
                        </a>
                        <button type="button" onclick="openDeleteModal('{{ route('engines.destroy', $engine->id) }}', '{{ $engine->name }}')" class="px-2.5 py-1 bg-[#21262d] hover:bg-[#f85149]/20 hover:border-[#f85149] hover:text-[#f85149] border border-[#30363d] rounded-md text-xs font-medium text-[#8b949e] transition-colors" title="Delete Engine">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                    <span class="text-xs text-[#8b949e]">
                        Gateway: <code class="text-[#c9d1d9] text-[11px] font-mono">/api/v1/engine/{{ $engine->id }}/{endpoint}</code>
                    </span>
                    <span class="text-xs text-[#8b949e]">{{ number_format($engine->logs_count) }} requests today</span>
                </div>
            </li>
        @empty
            <li class="p-8 text-center text-[#8b949e] text-sm">
                Belum ada AI Engine yang diregistrasikan.
            </li>
        @endforelse
    </ul>
</div>

<!-- ============================================== -->
<!-- CUSTOM DELETE CONFIRMATION MODAL               -->
<!-- ============================================== -->
<div id="deleteModal" class="fixed inset-0 z-50 hidden overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-[#010409] bg-opacity-80 transition-opacity" onclick="closeDeleteModal()"></div>

    <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
        <div class="relative transform overflow-hidden rounded-lg bg-[#0d1117] border border-[#30363d] text-left shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-md p-5">
            <div class="flex items-center space-x-3 mb-4">
                <div class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-[#f85149]/10 text-[#f85149] border border-[#f85149]/20">
                    <i class="fa-solid fa-triangle-exclamation text-base"></i>
                </div>
                <div>
                    <h3 class="text-sm font-semibold text-[#c9d1d9]" id="modal-title">Hapus AI Engine</h3>
                    <p class="text-xs text-[#8b949e]">Tindakan ini tidak dapat dibatalkan.</p>
                </div>
            </div>
            
            <p class="text-xs text-[#c9d1d9] mb-5 leading-relaxed">
                Apakah Anda yakin ingin menghapus engine <span id="engineNameToDelete" class="font-semibold text-white"></span> dari daftar mikrolayanan?
            </p>

            <form id="deleteForm" method="POST" class="flex justify-end space-x-2">
                @csrf
                @method('DELETE')
                <button type="button" onclick="closeDeleteModal()" class="bg-[#21262d] border border-[#30363d] hover:bg-[#30363d] px-3 py-1.5 rounded-md text-[#c9d1d9] text-xs font-semibold transition-colors">
                    Batal
                </button>
                <button type="submit" class="bg-[#f85149] hover:bg-[#da3633] text-white px-3 py-1.5 rounded-md text-xs font-semibold transition-colors">
                    Ya, Hapus
                </button>
            </form>
        </div>
    </div>
</div>

<script>
    function openDeleteModal(actionUrl, engineName) {
        document.getElementById('deleteForm').action = actionUrl;
        document.getElementById('engineNameToDelete').innerText = `"${engineName}"`;
        document.getElementById('deleteModal').classList.remove('hidden');
    }

    function closeDeleteModal() {
        document.getElementById('deleteModal').classList.add('hidden');
    }
</script>
@endsection