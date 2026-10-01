<?php

namespace App\Http\Controllers;

use App\Models\AiEngine;
use App\Models\AiLog;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;

class ApiGatewayController extends Controller
{
    public function forward(Request $request, $engine_id, $endpoint)
    {
        $engine = AiEngine::findOrFail($engine_id);

        if (!$engine->is_active) {
            return response()->json(['status' => 'error', 'message' => 'AI Engine sedang dinonaktifkan'], 403);
        }

        $startTime = microtime(true);
        $targetUrl = rtrim($engine->base_url, '/') . '/' . ltrim($endpoint, '/');
        
        try {
            // Persiapkan opsi request
            $options = [];
            if ($request->isMethod('GET')) {
                $options['query'] = $request->query();
            } else {
                $options['json'] = $request->all();
            }

            $response = Http::timeout(120)->withHeaders([
                'Authorization' => $engine->api_key ? 'Bearer ' . $engine->api_key : '',
                'Accept' => 'application/json'
            ])->send($request->method(), $targetUrl, $options);
            
            $statusCode = $response->status();
            $body = $response->json(); // Ambil sebagai array
            
        } catch (\Exception $e) {
            $statusCode = 500;
            $body = [
                'status' => 'error', 
                'message' => 'Gagal terhubung ke AI Engine (Python Error / Timeout).', 
                'details' => $e->getMessage()
            ];
        }

        $latency = (microtime(true) - $startTime) * 1000;

        AiLog::create([
            'ai_engine_id' => $engine->id,
            'endpoint_accessed' => $endpoint,
            'client_ip' => $request->ip(),
            'status_code' => $statusCode,
            'response_time_ms' => $latency
        ]);

        return response()->json($body, $statusCode);
    }
}