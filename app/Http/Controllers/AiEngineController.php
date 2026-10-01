<?php

namespace App\Http\Controllers;

use App\Models\AiEngine;
use Illuminate\Http\Request;
use Illuminate\Support\Str;

class AiEngineController extends Controller
{
    public function index()
    {
        $engines = AiEngine::withCount(['logs' => function ($query) {
            $query->whereDate('created_at', today());
        }])->get();

        return view('dashboard', compact('engines'));
    }

    public function create() 
    { 
        return view('engines.create'); 
    }

    public function store(Request $request)
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'type' => 'required|string|max:100',
            'base_url' => 'required|url|max:255',
            'is_active' => 'boolean'
        ]);
        
        // Generate otomatis API key
        $validated['api_key'] = 'aikey_' . Str::random(40);
        $validated['is_active'] = $request->has('is_active');
        
        $engine = AiEngine::create($validated);
        return redirect()->route('engines.show', $engine->id)->with('success', 'Engine berhasil didaftarkan.');
    }

    public function show($id)
    {
        $engine = AiEngine::with(['logs' => function($q) {
            $q->latest()->take(10);
        }])->findOrFail($id);

        return view('engines.show', compact('engine'));
    }

    public function generateKey($id)
    {
        $engine = AiEngine::findOrFail($id);
        $engine->update(['api_key' => 'aikey_' . Str::random(40)]);
        
        return back()->with('success', 'API Key berhasil diperbarui. Pastikan aplikasi klien mengupdate API Key mereka!');
    }

    // === TAMBAHKAN METHOD INI UNTUK MENGATASI ERROR EDIT & DELETE ===

    public function edit($id)
    {
        $engine = AiEngine::findOrFail($id);
        return view('engines.edit', compact('engine'));
    }

    public function update(Request $request, $id)
    {
        $engine = AiEngine::findOrFail($id);
        
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'type' => 'required|string|max:100',
            'base_url' => 'required|url|max:255',
            'is_active' => 'boolean'
        ]);
        
        $validated['is_active'] = $request->has('is_active');
        
        $engine->update($validated);
        
        return redirect()->route('engines.show', $engine->id)->with('success', 'Engine berhasil diperbarui.');
    }

    public function destroy($id)
    {
        $engine = AiEngine::findOrFail($id);
        $engine->delete();
        
        return redirect()->route('dashboard')->with('success', 'Engine berhasil dihapus.');
    }
}