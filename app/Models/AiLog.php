<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class AiLog extends Model
{
    protected $fillable = [
        'ai_engine_id',
        'endpoint_accessed',
        'client_ip',
        'status_code',
        'response_time_ms'
    ];

    public function engine(): BelongsTo
    {
        return $this->belongsTo(AiEngine::class, 'ai_engine_id');
    }
}