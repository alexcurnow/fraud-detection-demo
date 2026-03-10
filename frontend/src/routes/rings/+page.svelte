<script lang="ts">
	const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

	let rings = $state<any>(null);
	let isLoading = $state(true);
	let explanations = $state<Record<string, {text: string, loading: boolean}>>({});

	// Ring type metadata
	const ringTypeInfo: Record<string, {title: string, icon: string, color: string, description: string}> = {
		device_sharing: {
			title: 'Device Sharing',
			icon: '📱',
			color: 'red',
			description: 'Multiple accounts using the same device'
		},
		money_mule: {
			title: 'Money Mule Network',
			icon: '💸',
			color: 'orange',
			description: 'Chain of rapid fund transfers'
		},
		merchant_collusion: {
			title: 'Merchant Collusion',
			icon: '🏪',
			color: 'purple',
			description: 'Multiple users with suspicious merchant patterns'
		},
		account_takeover: {
			title: 'Account Takeover',
			icon: '🔓',
			color: 'yellow',
			description: 'Coordinated device/location changes'
		},
		synthetic_identity: {
			title: 'Synthetic Identity',
			icon: '👤',
			color: 'blue',
			description: 'Accounts created together with similar attributes'
		}
	};

	// Load fraud rings
	async function loadRings() {
		isLoading = true;
		try {
			const res = await fetch(`${API_BASE}/network/rings`);
			rings = await res.json();
		} catch (err) {
			console.error('Failed to load fraud rings:', err);
		} finally {
			isLoading = false;
		}
	}

	// Get LLM explanation for a ring type
	async function explainRingType(ringType: string) {
		explanations[ringType] = { text: '', loading: true };

		try {
			const res = await fetch(`${API_BASE}/explain/network/${ringType}`, {
				method: 'POST'
			});
			const data = await res.json();
			explanations[ringType] = { text: data.explanation, loading: false };
		} catch (err) {
			console.error(`Failed to explain ${ringType}:`, err);
			explanations[ringType] = {
				text: 'Failed to generate explanation. Please try again.',
				loading: false
			};
		}
	}

	// Format ring metadata for display
	function formatMetadata(metadata: any, ringType: string) {
		if (ringType === 'money_mule') {
			return [
				{ label: 'Hops', value: metadata.hops },
				{ label: 'Total Amount', value: `$${metadata.total_amount.toFixed(2)}` },
				{ label: 'Timespan', value: formatTimespan(metadata.first_transfer, metadata.last_transfer) }
			];
		} else if (ringType === 'merchant_collusion') {
			return [
				{ label: 'Merchant', value: metadata.merchant_name },
				{ label: 'Category', value: metadata.merchant_category },
				{ label: 'Transactions', value: metadata.transaction_count },
				{ label: 'Total Amount', value: `$${metadata.total_amount.toFixed(2)}` }
			];
		} else if (ringType === 'device_sharing') {
			return [
				{ label: 'Device ID', value: metadata.device_id },
				{ label: 'Transactions', value: metadata.transaction_count }
			];
		} else if (ringType === 'synthetic_identity') {
			return [
				{ label: 'Shared Devices', value: metadata.shared_devices },
				{ label: 'Creation Week', value: metadata.creation_week }
			];
		}
		return [];
	}

	function formatTimespan(start: string, end: string) {
		const diff = new Date(end).getTime() - new Date(start).getTime();
		const hours = Math.floor(diff / (1000 * 60 * 60));
		return `${hours} hours`;
	}

	// Load rings on mount
	$effect(() => {
		loadRings();
	});
</script>

<div class="max-w-7xl mx-auto px-4 py-8">
	<!-- Header -->
	<div class="mb-8">
		<h1 class="text-4xl font-bold text-gray-900 mb-2">Fraud Ring Detection</h1>
		<p class="text-gray-600">AI-powered network analysis to detect organized fraud patterns</p>
	</div>

	{#if isLoading}
		<div class="text-center py-12">
			<div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
			<p class="mt-4 text-gray-600">Analyzing transaction networks...</p>
		</div>
	{:else if rings}
		<!-- Summary Stats -->
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
			<div class="bg-white rounded-lg shadow-sm p-6">
				<div class="text-sm font-medium text-gray-500 mb-1">Total Rings Detected</div>
				<div class="text-3xl font-bold text-gray-900">{rings.total_rings}</div>
			</div>

			<div class="bg-white rounded-lg shadow-sm p-6">
				<div class="text-sm font-medium text-gray-500 mb-1">Ring Types</div>
				<div class="text-3xl font-bold text-blue-600">{Object.keys(rings.rings_by_type).length}</div>
			</div>

			<div class="bg-white rounded-lg shadow-sm p-6">
				<div class="text-sm font-medium text-gray-500 mb-1">Highest Count</div>
				<div class="text-3xl font-bold text-red-600">
					{Math.max(...Object.values(rings.rings_by_type))}
				</div>
			</div>
		</div>

		<!-- Ring Type Breakdown -->
		<div class="bg-white rounded-lg shadow-sm p-6 mb-8">
			<h2 class="text-xl font-bold text-gray-900 mb-4">Detection Summary</h2>
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
				{#each Object.entries(rings.rings_by_type) as [ringType, count]}
					{@const info = ringTypeInfo[ringType]}
					{#if info}
						<div class="text-center p-4 bg-gray-50 rounded-lg">
							<div class="text-3xl mb-2">{info.icon}</div>
							<div class="text-2xl font-bold text-{info.color}-600">{count}</div>
							<div class="text-sm font-medium text-gray-700">{info.title}</div>
						</div>
					{/if}
				{/each}
			</div>
		</div>

		<!-- Detected Rings by Type -->
		{#each Object.entries(rings.rings_by_type).filter(([_, count]) => count > 0) as [ringType, count]}
			{@const info = ringTypeInfo[ringType]}
			{@const ringsOfType = rings.all_rings.filter((r: any) => r.ring_type === ringType)}

			{#if info}
				<div class="bg-white rounded-lg shadow-sm p-6 mb-6 border-l-4 border-{info.color}-500">
					<!-- Ring Type Header -->
					<div class="flex items-start justify-between mb-4">
						<div>
							<div class="flex items-center gap-3 mb-2">
								<span class="text-3xl">{info.icon}</span>
								<h2 class="text-2xl font-bold text-gray-900">{info.title}</h2>
								<span class="px-3 py-1 bg-{info.color}-100 text-{info.color}-800 text-sm font-medium rounded-full">
									{count} detected
								</span>
							</div>
							<p class="text-gray-600">{info.description}</p>
						</div>

						<!-- Explain Button -->
						<button
							onclick={() => explainRingType(ringType)}
							disabled={explanations[ringType]?.loading}
							class="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
						>
							{#if explanations[ringType]?.loading}
								<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
								Generating...
							{:else}
								✨ Explain with AI
							{/if}
						</button>
					</div>

					<!-- LLM Explanation -->
					{#if explanations[ringType]?.text}
						<div class="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
							<div class="flex items-start gap-2 mb-2">
								<span class="text-lg">🤖</span>
								<div class="font-semibold text-blue-900">AI Analysis</div>
							</div>
							<div class="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
								{explanations[ringType].text}
							</div>
						</div>
					{/if}

					<!-- Ring Details -->
					<div class="space-y-4">
						{#each ringsOfType.slice(0, 3) as ring, idx}
							{@const metadata = formatMetadata(ring.metadata, ringType)}
							<div class="p-4 bg-gray-50 rounded-lg">
								<div class="flex items-start justify-between mb-3">
									<div class="font-semibold text-gray-900">Ring #{idx + 1}</div>
									<span class="px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded">
										{ring.confidence} confidence
									</span>
								</div>

								<!-- Metadata -->
								{#if metadata.length > 0}
									<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
										{#each metadata as item}
											<div>
												<div class="text-xs font-medium text-gray-500">{item.label}</div>
												<div class="text-sm font-semibold text-gray-900">{item.value}</div>
											</div>
										{/each}
									</div>
								{/if}

								<!-- Accounts Involved -->
								<div>
									<div class="text-xs font-medium text-gray-500 mb-1">
										Accounts Involved ({ring.account_count})
									</div>
									<div class="flex flex-wrap gap-2">
										{#each ring.accounts.slice(0, 8) as accountId}
											<span class="px-2 py-1 bg-white border border-gray-300 text-xs font-mono rounded">
												{accountId.slice(0, 12)}...
											</span>
										{/each}
										{#if ring.account_count > 8}
											<span class="px-2 py-1 bg-gray-200 text-gray-600 text-xs font-medium rounded">
												+{ring.account_count - 8} more
											</span>
										{/if}
									</div>
								</div>
							</div>
						{/each}

						{#if ringsOfType.length > 3}
							<div class="text-sm text-gray-500 text-center py-2">
								and {ringsOfType.length - 3} more {info.title.toLowerCase()} rings...
							</div>
						{/if}
					</div>
				</div>
			{/if}
		{/each}
	{:else}
		<div class="text-center py-12 bg-white rounded-lg shadow-sm">
			<p class="text-gray-600">No fraud rings detected</p>
		</div>
	{/if}
</div>
