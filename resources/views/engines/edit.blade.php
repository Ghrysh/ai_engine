@extends('layouts.app')

@section('content')
<div class="mb-5">
    <a href="{{ route('dashboard') }}" class="text-[#58a6ff] hover:underline text-sm font-medium flex items-center gap-1 w-max">
        <i class="fa-solid fa-arrow-left"></i> Back to engines
    </a>
</div>

<div class="flex justify-between items-center mb-5">
    <h1 class="text-2xl font-normal text-[#c9d1d9]">Edit Engine: {{ $engine->name }}</h1>
</div>

<div class="bg-[#0d1117] border border-[#30363d] rounded-md max-w-2xl">
    <div class="bg-[#161b22] border-b border-[#30363d] px-4 py-3 text-sm font-semibold text-[#c9d1d9]">
        Engine Configuration
    </div>
    
    <form action="{{ route('engines.update', $engine) }}" method="POST" class="p-5">
        @csrf
        @method('PUT')
        
        <div class="mb-4">
            <label class="block text-sm font-medium text-[#c9d1d9] mb-1">Engine Name</label>
            <input type="text" name="name" value="{{ old('name', $engine->name) }}" required class="w-full bg-[#010409] border border-[#30363d] rounded-md px-3 py-1.5 text-sm text-[#c9d1d9] focus:outline-none focus:border-[#58a6ff] focus:ring-1 focus:ring-[#58a6ff]">
        </div>

        <div class="mb-4">
            <label class="block text-sm font-medium text-[#c9d1d9] mb-1">Service Type</label>
            <select name="type" required class="w-full bg-[#010409] border border-[#30363d] rounded-md px-3 py-1.5 text-sm text-[#c9d1d9] focus:outline-none focus:border-[#58a6ff] focus:ring-1 focus:ring-[#58a6ff]">
                <option value="NLP" {{ $engine->type == 'NLP' ? 'selected' : '' }}>NLP Analysis</option>
                <option value="Analytics" {{ $engine->type == 'Analytics' ? 'selected' : '' }}>Big Data Analytics</option>
                <option value="Scraping" {{ $engine->type == 'Scraping' ? 'selected' : '' }}>Web Scraping Worker</option>
                <option value="Prediction" {{ $engine->type == 'Prediction' ? 'selected' : '' }}>Predictive Model</option>
            </select>
        </div>

        <div class="mb-4">
            <label class="block text-sm font-medium text-[#c9d1d9] mb-1">Target Base URL (Internal Python Service)</label>
            <input type="url" name="base_url" value="{{ old('base_url', $engine->base_url) }}" required class="w-full bg-[#010409] border border-[#30363d] rounded-md px-3 py-1.5 text-sm text-[#c9d1d9] focus:outline-none focus:border-[#58a6ff] focus:ring-1 focus:ring-[#58a6ff]">
            <p class="text-xs text-[#8b949e] mt-1"><i class="fa-solid fa-circle-info mr-1"></i> URL tempat script FastAPI/Flask berjalan.</p>
        </div>

        <div class="mb-5">
            <label class="block text-sm font-medium text-[#c9d1d9] mb-1">Authorization Token (Opsional)</label>
            <input type="text" name="api_key" value="{{ old('api_key', $engine->api_key) }}" placeholder="Bearer Token if required" class="w-full bg-[#010409] border border-[#30363d] rounded-md px-3 py-1.5 text-sm text-[#c9d1d9] focus:outline-none focus:border-[#58a6ff] focus:ring-1 focus:ring-[#58a6ff]">
        </div>

        <div class="mb-6 flex items-center gap-2">
            <input type="checkbox" name="is_active" id="is_active" value="1" {{ $engine->is_active ? 'checked' : '' }} class="rounded border-[#30363d] bg-[#010409] text-[#238636] focus:ring-[#238636]">
            <label for="is_active" class="text-sm font-medium text-[#c9d1d9]">Active (Enable API Gateway routing)</label>
        </div>

        <div class="pt-4 border-t border-[#30363d] flex gap-3">
            <button type="submit" class="bg-[#238636] hover:bg-[#2ea043] text-white text-sm font-semibold py-1.5 px-4 border border-[rgba(240,246,252,0.1)] rounded-md shadow-sm transition-colors">
                Update Engine
            </button>
            <a href="{{ route('dashboard') }}" class="bg-[#21262d] hover:bg-[#30363d] text-[#c9d1d9] text-sm font-semibold py-1.5 px-4 border border-[#363b42] rounded-md shadow-sm transition-colors">
                Cancel
            </a>
        </div>
    </form>
</div>
@endsection
