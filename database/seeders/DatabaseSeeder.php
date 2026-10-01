<?php

namespace Database\Seeders;

use App\Models\AiEngine;
use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        User::updateOrCreate(
            ['email' => 'admin@ews.com'],
            [
                'name' => 'Administrator',
                'password' => Hash::make('admin123')
            ]
        );

        $engines = [
            [
                'name' => 'Data Scraper Engine',
                'type' => 'Scraping',
                'base_url' => 'http://scraping_api:8000',
                'is_active' => true,
            ],
            [
                'name' => 'EWS Big Data Analytics',
                'type' => 'Analytics',
                'base_url' => 'http://ews_ai_api:8000',
                'is_active' => true,
            ],
            [
                'name' => 'NLP Auto-Input Assistant',
                'type' => 'Prediction',
                'base_url' => 'http://ews_ai_api:8000',
                'is_active' => true,
            ],
        ];

        foreach ($engines as $engine) {
            AiEngine::updateOrCreate(
                ['name' => $engine['name']],
                $engine
            );
        }
    }
}