<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class AiEngine extends Model
{
    protected $fillable = [
        'name', 
        'type', 
        'base_url', 
        'api_key', 
        'is_active'
    ];

    public function logs(): HasMany
    {
        return $this->hasMany(AiLog::class);
    }
}