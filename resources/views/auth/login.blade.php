<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign in to AI Manager</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
    </style>
</head>
<body class="bg-[#0d1117] text-[#c9d1d9] antialiased min-h-screen flex flex-col items-center justify-center py-10 px-4">
    
    <!-- Logo -->
    <div class="mb-6 text-center">
        <i class="fa-solid fa-microchip text-5xl text-white mb-4"></i>
        <h1 class="text-2xl font-normal tracking-tight text-white">Sign in to AI Manager</h1>
    </div>

    <!-- Login Card -->
    <div class="w-full max-w-[340px] bg-[#161b22] border border-[#30363d] rounded-xl p-4 shadow-xl">
        <form action="{{ route('login') }}" method="POST">
            @csrf
            
            @if($errors->any())
            <div class="mb-4 px-3 py-2 bg-[rgba(248,81,73,0.1)] border border-[rgba(248,81,73,0.4)] text-[#f85149] rounded-md text-sm">
                {{ $errors->first() }}
            </div>
            @endif

            <div class="mb-4">
                <label for="email" class="block text-sm font-medium text-[#c9d1d9] mb-2">Email address</label>
                <input type="email" name="email" id="email" value="{{ old('email') }}" required autofocus
                    class="w-full px-3 py-1.5 bg-[#0d1117] border border-[#30363d] rounded-md text-[#c9d1d9] focus:outline-none focus:border-[#58a6ff] focus:ring-1 focus:ring-[#58a6ff] transition-colors shadow-sm">
            </div>

            <div class="mb-5">
                <div class="flex justify-between items-center mb-2">
                    <label for="password" class="block text-sm font-medium text-[#c9d1d9]">Password</label>
                </div>
                <input type="password" name="password" id="password" required
                    class="w-full px-3 py-1.5 bg-[#0d1117] border border-[#30363d] rounded-md text-[#c9d1d9] focus:outline-none focus:border-[#58a6ff] focus:ring-1 focus:ring-[#58a6ff] transition-colors shadow-sm">
            </div>

            <button type="submit" class="w-full bg-[#238636] hover:bg-[#2ea043] text-white font-semibold py-1.5 px-4 rounded-md border border-[rgba(240,246,252,0.1)] transition-colors shadow-sm">
                Sign in
            </button>
        </form>
    </div>
    
    <p class="mt-16 text-xs text-[#8b949e] text-center">
        &copy; 2026 EWS AI Integration.
    </p>

</body>
</html>