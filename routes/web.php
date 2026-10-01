<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\AiEngineController;
use App\Http\Controllers\AiLogController;
use App\Http\Controllers\Auth\LoginController;

Route::get('/login', [LoginController::class, 'showLoginForm'])->name('login');
Route::post('/login', [LoginController::class, 'login']);
Route::post('/logout', [LoginController::class, 'logout'])->name('logout');

Route::middleware('auth')->group(function () {
    Route::get('/', [AiEngineController::class, 'index'])->name('dashboard');
    Route::get('/logs', [AiLogController::class, 'index'])->name('logs');
    
    // Hapus 'show' dari dalam except() agar Route engines.show aktif
    Route::resource('engines', AiEngineController::class)->except(['index']);
    
    // Rute untuk Generate API Key
    Route::post('/engines/{id}/generate-key', [AiEngineController::class, 'generateKey'])->name('engines.generate-key');
});