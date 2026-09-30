<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Engine Manager</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif; }
    </style>
</head>
<body class="bg-[#0d1117] text-[#c9d1d9] antialiased min-h-screen flex flex-col">
    
    <!-- Navbar -->
    <nav class="bg-[#161b22] border-b border-[#30363d] px-4 py-3 flex items-center justify-between">
        <div class="flex items-center space-x-4">
            <i class="fa-solid fa-microchip text-xl text-[#c9d1d9]"></i>
            <span class="font-semibold text-sm tracking-wide text-white">AI Engine Manager</span>
            <div class="hidden md:flex space-x-1 pl-4 text-sm font-medium">
                <a href="#" class="px-3 py-1.5 bg-[#21262d] text-white border border-[#30363d] rounded-md">Overview</a>
                <a href="#" class="px-3 py-1.5 text-[#c9d1d9] hover:bg-[#21262d] hover:rounded-md transition-colors">Engines</a>
                <a href="#" class="px-3 py-1.5 text-[#c9d1d9] hover:bg-[#21262d] hover:rounded-md transition-colors">API Logs</a>
            </div>
        </div>
        <div class="text-sm font-medium text-[#c9d1d9] hover:text-white cursor-pointer">
            <i class="fa-regular fa-circle-user mr-1"></i> Administrator
        </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-6xl w-full mx-auto px-4 py-8 flex-grow">
        @yield('content')
    </main>

</body>
</html>