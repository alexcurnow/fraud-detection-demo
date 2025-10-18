<script lang="ts">
	const API_BASE = 'http://localhost:8000';

	let searchQuery = $state('');
	let searchResults = $state<any[]>([]);
	let showDropdown = $state(false);
	let selectedUser = $state<any>(null);
	let transactionResult = $state<any>(null);
	let flaggedTransactions = $state<any[]>([]);
	let isLoading = $state(false);

	// Transaction form state
	let amount = $state('');
	let merchantName = $state('');
	let merchantCategory = $state('');
	let latitude = $state('');
	let longitude = $state('');

	// Search users as you type
	async function searchUsers() {
		if (searchQuery.length < 1) {
			searchResults = [];
			showDropdown = false;
			return;
		}

		try {
			const res = await fetch(`${API_BASE}/users/search?q=${encodeURIComponent(searchQuery)}`);
			searchResults = await res.json();
			showDropdown = true;
		} catch (err) {
			console.error('Search failed:', err);
		}
	}

	// Select a user and fetch their details
	async function selectUser(user: any) {
		isLoading = true;
		try {
			const res = await fetch(`${API_BASE}/users/${user.account_id}`);
			selectedUser = await res.json();
			searchQuery = user.email;
			showDropdown = false;
			transactionResult = null;
		} catch (err) {
			console.error('Failed to fetch user:', err);
		} finally {
			isLoading = false;
		}
	}

	// Submit transaction
	async function submitTransaction() {
		if (!selectedUser) return;

		isLoading = true;
		try {
			const res = await fetch(`${API_BASE}/users/${selectedUser.account_id}/transactions`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					amount: parseFloat(amount),
					merchant_name: merchantName,
					merchant_category: merchantCategory,
					latitude: latitude ? parseFloat(latitude) : null,
					longitude: longitude ? parseFloat(longitude) : null
				})
			});
			transactionResult = await res.json();

			// Refresh flagged transactions
			loadFlaggedTransactions();
		} catch (err) {
			console.error('Transaction failed:', err);
		} finally {
			isLoading = false;
		}
	}

	// Load flagged transactions
	async function loadFlaggedTransactions() {
		try {
			const res = await fetch(`${API_BASE}/transactions/flagged?limit=5`);
			const data = await res.json();
			flaggedTransactions = data.transactions;
		} catch (err) {
			console.error('Failed to load flagged transactions:', err);
		}
	}

	// Load flagged transactions on mount
	$effect(() => {
		loadFlaggedTransactions();
	});
</script>

<div class="min-h-screen bg-gray-50">
	<div class="max-w-7xl mx-auto px-4 py-8">
		<!-- Header -->
		<div class="mb-8">
			<h1 class="text-4xl font-bold text-gray-900 mb-2">Fraud Detection Demo</h1>
			<p class="text-gray-600">Select a user and test transaction fraud detection in real-time</p>
		</div>

		<!-- User Search -->
		<div class="bg-white rounded-lg shadow-sm p-6 mb-6">
			<label for="user-search" class="block text-sm font-medium text-gray-700 mb-2">
				Search for a user
			</label>
			<div class="relative">
				<input
					id="user-search"
					type="text"
					bind:value={searchQuery}
					oninput={searchUsers}
					onfocus={() => { if (searchResults.length > 0) showDropdown = true; }}
					placeholder="Search by email or account ID..."
					class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				/>

				{#if showDropdown && searchResults.length > 0}
					<div class="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-auto">
						{#each searchResults as user}
							<button
								onclick={() => selectUser(user)}
								class="w-full px-4 py-3 text-left hover:bg-gray-50 focus:bg-gray-50 border-b border-gray-100 last:border-b-0"
							>
								<div class="font-medium text-gray-900">{user.email}</div>
								<div class="text-sm text-gray-500">{user.account_id}</div>
							</button>
						{/each}
					</div>
				{/if}
			</div>
		</div>

		{#if isLoading}
			<div class="text-center py-12">
				<div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
			</div>
		{/if}

		{#if selectedUser}
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
				<!-- User Pattern Card -->
				<div class="bg-white rounded-lg shadow-sm p-6">
					<h2 class="text-xl font-bold text-gray-900 mb-4">User Profile: {selectedUser.email}</h2>

					<div class="space-y-3">
						<div>
							<span class="text-sm font-medium text-gray-500">Account ID:</span>
							<span class="ml-2 text-sm text-gray-900">{selectedUser.account_id}</span>
						</div>

						<div>
							<span class="text-sm font-medium text-gray-500">Total Transactions:</span>
							<span class="ml-2 text-sm text-gray-900">{selectedUser.patterns.total_transactions}</span>
						</div>

						<div>
							<span class="text-sm font-medium text-gray-500">Avg Transaction:</span>
							<span class="ml-2 text-sm text-gray-900">${selectedUser.patterns.avg_transaction_amount.toFixed(2)}</span>
						</div>

						<div>
							<span class="text-sm font-medium text-gray-500">Common Merchants:</span>
							<div class="mt-1 flex flex-wrap gap-2">
								{#each selectedUser.patterns.common_merchants as merchant}
									<span class="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">{merchant}</span>
								{/each}
							</div>
						</div>

						<div>
							<span class="text-sm font-medium text-gray-500">Typical Hours:</span>
							<div class="mt-1 flex flex-wrap gap-2">
								{#each selectedUser.patterns.typical_hours as hour}
									<span class="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">{hour}:00</span>
								{/each}
							</div>
						</div>

						{#if selectedUser.patterns.home_location.latitude}
							<div>
								<span class="text-sm font-medium text-gray-500">Home Location:</span>
								<span class="ml-2 text-sm text-gray-900">
									{selectedUser.patterns.home_location.latitude.toFixed(2)}, {selectedUser.patterns.home_location.longitude.toFixed(2)}
								</span>
							</div>
						{/if}

						<div>
							<span class="text-sm font-medium text-gray-500">Fraud Flags:</span>
							<span class="ml-2 text-sm font-medium {selectedUser.patterns.fraud_flags > 0 ? 'text-red-600' : 'text-green-600'}">
								{selectedUser.patterns.fraud_flags}
							</span>
						</div>
					</div>
				</div>

				<!-- Transaction Form -->
				<div class="bg-white rounded-lg shadow-sm p-6">
					<h2 class="text-xl font-bold text-gray-900 mb-4">Submit Test Transaction</h2>

					<form onsubmit={(e) => { e.preventDefault(); submitTransaction(); }} class="space-y-4">
						<div>
							<label for="amount" class="block text-sm font-medium text-gray-700 mb-1">Amount ($)</label>
							<input
								id="amount"
								type="number"
								step="0.01"
								bind:value={amount}
								required
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
								placeholder="45.50"
							/>
						</div>

						<div>
							<label for="merchant" class="block text-sm font-medium text-gray-700 mb-1">Merchant Name</label>
							<input
								id="merchant"
								type="text"
								bind:value={merchantName}
								required
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
								placeholder="Local Grocery Store"
							/>
						</div>

						<div>
							<label for="category" class="block text-sm font-medium text-gray-700 mb-1">Merchant Category</label>
							<select
								id="category"
								bind:value={merchantCategory}
								required
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							>
								<option value="">Select category...</option>
								<option value="grocery">Grocery</option>
								<option value="restaurant">Restaurant</option>
								<option value="electronics">Electronics</option>
								<option value="clothing">Clothing</option>
								<option value="gas_station">Gas Station</option>
								<option value="pharmacy">Pharmacy</option>
								<option value="travel">Travel</option>
								<option value="entertainment">Entertainment</option>
								<option value="online">Online</option>
							</select>
						</div>

						<div class="grid grid-cols-2 gap-4">
							<div>
								<label for="lat" class="block text-sm font-medium text-gray-700 mb-1">Latitude</label>
								<input
									id="lat"
									type="number"
									step="0.0001"
									bind:value={latitude}
									class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
									placeholder="Optional"
								/>
							</div>
							<div>
								<label for="lng" class="block text-sm font-medium text-gray-700 mb-1">Longitude</label>
								<input
									id="lng"
									type="number"
									step="0.0001"
									bind:value={longitude}
									class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
									placeholder="Optional"
								/>
							</div>
						</div>

						<button
							type="submit"
							disabled={isLoading}
							class="w-full px-4 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
						>
							{isLoading ? 'Processing...' : 'Submit Transaction'}
						</button>
					</form>
				</div>
			</div>

			<!-- Transaction Result -->
			{#if transactionResult}
				<div class="bg-white rounded-lg shadow-sm p-6 mb-6 border-l-4 {transactionResult.fraud_analysis.is_flagged ? 'border-red-500' : 'border-green-500'}">
					<div class="flex items-start justify-between mb-4">
						<h2 class="text-xl font-bold text-gray-900">Transaction Result</h2>
						<span class="px-3 py-1 text-sm font-medium rounded-full {transactionResult.fraud_analysis.is_flagged ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}">
							{transactionResult.status.toUpperCase()}
						</span>
					</div>

					<div class="grid grid-cols-2 gap-4 mb-4">
						<div>
							<span class="text-sm font-medium text-gray-500">Transaction ID:</span>
							<span class="ml-2 text-sm text-gray-900">{transactionResult.transaction_id}</span>
						</div>
						<div>
							<span class="text-sm font-medium text-gray-500">Amount:</span>
							<span class="ml-2 text-sm text-gray-900">${transactionResult.amount.toFixed(2)}</span>
						</div>
						<div>
							<span class="text-sm font-medium text-gray-500">Merchant:</span>
							<span class="ml-2 text-sm text-gray-900">{transactionResult.merchant_name}</span>
						</div>
						<div>
							<span class="text-sm font-medium text-gray-500">Category:</span>
							<span class="ml-2 text-sm text-gray-900">{transactionResult.merchant_category}</span>
						</div>
					</div>

					<div class="border-t pt-4">
						<h3 class="text-lg font-semibold text-gray-900 mb-3">Fraud Analysis</h3>

						<div class="mb-3">
							<div class="flex items-center justify-between mb-1">
								<span class="text-sm font-medium text-gray-700">Risk Score:</span>
								<span class="text-2xl font-bold {transactionResult.fraud_analysis.risk_score > 0.5 ? 'text-red-600' : 'text-green-600'}">
									{(transactionResult.fraud_analysis.risk_score * 100).toFixed(1)}%
								</span>
							</div>
							<div class="w-full bg-gray-200 rounded-full h-3">
								<div
									class="h-3 rounded-full {transactionResult.fraud_analysis.risk_score > 0.5 ? 'bg-red-600' : 'bg-green-600'}"
									style="width: {transactionResult.fraud_analysis.risk_score * 100}%"
								></div>
							</div>
						</div>

						{#if transactionResult.fraud_analysis.flagged_reasons.length > 0}
							<div>
								<span class="text-sm font-medium text-gray-700 block mb-2">Flagged Reasons:</span>
								<div class="space-y-2">
									{#each transactionResult.fraud_analysis.flagged_reasons as reason}
										<div class="px-3 py-2 bg-red-50 border border-red-200 rounded text-sm text-red-800">
											{reason.replace(/_/g, ' ').toUpperCase()}
										</div>
									{/each}
								</div>
							</div>
						{/if}

						<div class="mt-3">
							<span class="text-xs text-gray-500">Model Version: {transactionResult.fraud_analysis.model_version}</span>
						</div>
					</div>
				</div>
			{/if}
		{/if}

		<!-- Flagged Transactions -->
		{#if flaggedTransactions.length > 0}
			<div class="bg-white rounded-lg shadow-sm p-6">
				<h2 class="text-xl font-bold text-gray-900 mb-4">Recent Flagged Transactions</h2>
				<div class="overflow-x-auto">
					<table class="w-full">
						<thead class="bg-gray-50 border-b">
							<tr>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Merchant</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk Score</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reasons</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-gray-200">
							{#each flaggedTransactions as txn}
								<tr class="hover:bg-gray-50">
									<td class="px-4 py-3 text-sm text-gray-900">{txn.user_email}</td>
									<td class="px-4 py-3 text-sm text-gray-900">${txn.amount.toFixed(2)}</td>
									<td class="px-4 py-3 text-sm text-gray-900">
										<div>{txn.merchant_name}</div>
										<div class="text-xs text-gray-500">{txn.merchant_category}</div>
									</td>
									<td class="px-4 py-3">
										<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
											{(txn.risk_score * 100).toFixed(0)}%
										</span>
									</td>
									<td class="px-4 py-3 text-xs text-gray-600">
										{txn.flagged_reasons.slice(0, 2).join(', ')}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{/if}
	</div>
</div>
