<?php

namespace App\Http\Controllers;

use App\Models\AiLog;
use App\Models\AiEngine;
use Illuminate\Http\Request;

class AiLogController extends Controller
{
    public function index(Request $request)
    {
        $engines = AiEngine::all();

        $logs = AiLog::with('engine')
            ->when($request->filled('engine_id'), function ($query) use ($request) {
                $query->where('ai_engine_id', $request->engine_id);
            })
            ->latest()
            ->paginate(20);
        
        return view('logs', compact('logs', 'engines'));
    }
}