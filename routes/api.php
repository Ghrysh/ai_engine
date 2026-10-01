<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\ApiGatewayController;

Route::any('/v1/engine/{engine_id}/{endpoint}', [ApiGatewayController::class, 'forward'])
    ->where('endpoint', '.*');