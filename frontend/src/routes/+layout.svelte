<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/stores';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="min-h-screen bg-gray-50">
	<!-- Navigation -->
	<nav class="bg-white shadow-sm border-b border-gray-200">
		<div class="max-w-7xl mx-auto px-4">
			<div class="flex items-center justify-between h-16">
				<div class="flex items-center gap-2">
					<span class="text-xl font-bold text-gray-900">🔍 Fraud Detection</span>
				</div>
				<div class="flex gap-1">
					<a
						href="/"
						class="px-4 py-2 rounded-lg font-medium transition-colors {$page.url.pathname === '/' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}"
					>
						Transactions
					</a>
					<a
						href="/rings"
						class="px-4 py-2 rounded-lg font-medium transition-colors {$page.url.pathname === '/rings' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}"
					>
						Fraud Rings
					</a>
				</div>
			</div>
		</div>
	</nav>

	<!-- Page content -->
	{@render children?.()}
</div>
