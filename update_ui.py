
html_content = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tali Workspace</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --sidebar-bg: #1e293b;
            --sidebar-text: #e2e8f0;
            --sidebar-hover: #334155;
            --main-bg: #f1f5f9;
            --card-bg: #ffffff;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--main-bg);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            overflow: hidden;
        }

        /* Sidebar */
        .sidebar {
            width: 280px;
            background-color: var(--sidebar-bg);
            color: var(--sidebar-text);
            display: flex;
            flex-direction: column;
            border-right: 1px solid #334155;
        }

        .sidebar-header {
            padding: 20px;
            border-bottom: 1px solid #334155;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .sidebar-header h1 {
            font-size: 1.25rem;
            font-weight: 600;
            color: white;
        }

        .sidebar-actions {
            padding: 15px;
        }

        .btn-new-customer {
            width: 100%;
            padding: 10px;
            background-color: var(--primary);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: background 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn-new-customer:hover {
            background-color: var(--primary-hover);
        }

        .customer-list {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }

        .customer-item {
            padding: 12px;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.2s;
            margin-bottom: 4px;
        }

        .customer-item:hover {
            background-color: var(--sidebar-hover);
        }

        .customer-item.active {
            background-color: var(--primary);
            color: white;
        }

        .customer-item.active .customer-email {
            color: rgba(255, 255, 255, 0.8);
        }

        .customer-name {
            font-weight: 500;
            font-size: 0.95rem;
        }

        .customer-email {
            font-size: 0.8rem;
            color: #94a3b8;
            margin-top: 2px;
        }

        .sidebar-footer {
            padding: 15px;
            border-top: 1px solid #334155;
            font-size: 0.8rem;
            color: #94a3b8;
            text-align: center;
        }

        /* Main Content */
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .top-bar {
            height: 60px;
            background-color: var(--card-bg);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            padding: 0 24px;
            justify-content: space-between;
        }

        .current-customer {
            font-weight: 600;
            font-size: 1.1rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-badge {
            font-size: 0.75rem;
            padding: 4px 8px;
            background-color: #dbeafe;
            color: #1e40af;
            border-radius: 12px;
            font-weight: 500;
        }

        .workspace {
            flex: 1;
            display: grid;
            grid-template-columns: 400px 1fr;
            overflow: hidden;
        }

        /* Left Panel: Controls */
        .panel-controls {
            background-color: var(--card-bg);
            border-right: 1px solid var(--border);
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            overflow-y: auto;
        }

        .control-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .control-label {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .select-input, .text-input {
            padding: 10px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-family: inherit;
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
        }

        .select-input:focus, .text-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
        }

        textarea.text-input {
            min-height: 150px;
            resize: vertical;
            line-height: 1.5;
        }

        .btn-generate {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            padding: 14px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.1s, box-shadow 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-top: 10px;
        }

        .btn-generate:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
        }

        .btn-generate:active {
            transform: translateY(0);
        }

        /* Right Panel: Preview */
        .panel-preview {
            background-color: #f8fafc;
            padding: 24px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .preview-card {
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            min-height: 100%;
            display: flex;
            flex-direction: column;
        }

        .preview-header {
            padding: 16px 24px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .preview-title {
            font-weight: 600;
            color: var(--text-main);
        }

        .preview-content {
            padding: 40px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #334155;
            white-space: pre-wrap;
        }

        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: var(--text-muted);
            text-align: center;
            padding: 20px;
        }

        .empty-icon {
            font-size: 3rem;
            margin-bottom: 16px;
            opacity: 0.5;
        }

        /* Modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            backdrop-filter: blur(2px);
        }

        .modal {
            background: white;
            padding: 24px;
            border-radius: 12px;
            width: 400px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        }

        .modal h2 {
            margin-bottom: 20px;
            font-size: 1.25rem;
        }

        .modal-actions {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            margin-top: 20px;
        }

        .btn-secondary {
            background: white;
            border: 1px solid var(--border);
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            color: var(--text-main);
        }

        .btn-primary {
            background: var(--primary);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
        }

        /* Toast */
        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            padding: 12px 24px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            display: none;
            animation: slideIn 0.3s ease-out;
        }

        .toast.success { background-color: #10b981; }
        .toast.error { background-color: #ef4444; }

        @keyframes slideIn {
            from { transform: translateY(100%); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
    </style>
</head>
<body>

    <!-- Sidebar -->
    <aside class="sidebar">
        <div class="sidebar-header">
            <div style="width: 24px; height: 24px; background: #3b82f6; border-radius: 6px;"></div>
            <h1>Tali Agent</h1>
        </div>
        
        <div class="sidebar-actions">
            <button class="btn-new-customer" onclick="openModal()">
                <span>+</span> Neuer Kunde
            </button>
            <button class="btn-secondary" onclick="syncCustomers()" style="width: 100%; margin-top: 8px; background: transparent; color: #94a3b8; border-color: #334155;">
                🔄 Sync Lexware
            </button>
        </div>

        <div class="customer-list" id="customerList">
            <!-- Customers will be loaded here -->
        </div>

        <div class="sidebar-footer">
            v1.0.0 • Connected to Lexware
        </div>
    </aside>

    <!-- Main Content -->
    <main class="main">
        <!-- Top Bar -->
        <header class="top-bar">
            <div class="current-customer" id="currentCustomerDisplay">
                <span style="color: var(--text-muted); font-weight: 400;">Kein Kunde ausgewählt</span>
            </div>
            <div class="user-profile">
                <!-- Placeholder for user profile -->
            </div>
        </header>

        <!-- Workspace Split View -->
        <div class="workspace">
            <!-- Left: Controls -->
            <div class="panel-controls">
                <div class="control-group">
                    <label class="control-label">Dokumenttyp</label>
                    <select id="docType" class="select-input">
                        <option value="angebot">Angebot</option>
                        <option value="rechnung">Rechnung</option>
                    </select>
                </div>

                <div class="control-group">
                    <label class="control-label">Anweisungen an die KI</label>
                    <textarea id="documentPrompt" class="text-input" placeholder="Beschreibe, was im Dokument stehen soll. Z.B.: 'Erstelle ein Angebot für Webdesign, 40 Stunden à 80€...'"></textarea>
                </div>

                <button class="btn-generate" onclick="generateDocument()">
                    <span>✨</span> Entwurf generieren
                </button>

                <div style="margin-top: auto; padding: 16px; background: #f8fafc; border-radius: 8px; font-size: 0.85rem; color: var(--text-muted);">
                    ℹ️ <strong>Hinweis:</strong> Alle Dokumente werden als Entwurf erstellt und müssen in Lexware finalisiert werden.
                </div>
            </div>

            <!-- Right: Preview -->
            <div class="panel-preview">
                <div class="preview-card">
                    <div class="preview-header">
                        <span class="preview-title">Vorschau</span>
                        <div class="preview-actions">
                            <!-- Actions like Copy/Download could go here -->
                        </div>
                    </div>
                    <div id="previewContent" class="preview-content">
                        <div class="empty-state">
                            <div class="empty-icon">📄</div>
                            <h3>Noch kein Dokument generiert</h3>
                            <p>Wähle einen Kunden und erstelle einen Entwurf.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- New Customer Modal -->
    <div id="customerModal" class="modal-overlay">
        <div class="modal">
            <h2>Neuen Kunden anlegen</h2>
            <div class="control-group" style="margin-bottom: 12px;">
                <label class="control-label">Name</label>
                <input type="text" id="newCustomerName" class="text-input">
            </div>
            <div class="control-group" style="margin-bottom: 12px;">
                <label class="control-label">E-Mail</label>
                <input type="email" id="newCustomerEmail" class="text-input">
            </div>
            <div class="control-group" style="margin-bottom: 12px;">
                <label class="control-label">Telefon</label>
                <input type="tel" id="newCustomerPhone" class="text-input">
            </div>
            <div class="control-group">
                <label class="control-label">Stadt</label>
                <input type="text" id="newCustomerCity" class="text-input">
            </div>
            <div class="modal-actions">
                <button class="btn-secondary" onclick="closeModal()">Abbrechen</button>
                <button class="btn-primary" onclick="createCustomer()">Speichern</button>
            </div>
        </div>
    </div>

    <!-- Toast Notification -->
    <div id="toast" class="toast"></div>

    <script>
        const API_URL = "http://127.0.0.1:8000";
        let selectedCustomerId = null;

        document.addEventListener("DOMContentLoaded", loadCustomers);

        // --- Customer Management ---

        async function loadCustomers() {
            try {
                const response = await fetch(`${API_URL}/customers`);
                const customers = await response.json();
                renderCustomerList(customers);
            } catch (error) {
                showToast("Fehler beim Laden der Kunden", "error");
            }
        }

        function renderCustomerList(customers) {
            const list = document.getElementById("customerList");
            list.innerHTML = "";

            customers.forEach(customer => {
                const div = document.createElement("div");
                div.className = `customer-item ${selectedCustomerId === customer.id ? 'active' : ''}`;
                div.onclick = () => selectCustomer(customer);
                div.innerHTML = `
                    <div class="customer-name">${customer.name}</div>
                    <div class="customer-email">${customer.email}</div>
                `;
                list.appendChild(div);
            });
        }

        function selectCustomer(customer) {
            selectedCustomerId = customer.id;
            
            // Update UI
            document.getElementById("currentCustomerDisplay").innerHTML = `
                <span>${customer.name}</span>
                <span class="status-badge">Aktiv</span>
            `;
            
            // Re-render list to update active state
            const items = document.querySelectorAll('.customer-item');
            items.forEach(item => item.classList.remove('active'));
            // Ideally we'd re-render, but for now just finding by text content is hacky but fast, 
            // let's just reload the list logic or simple class toggle
            // Simple class toggle:
            // (In a real app, use a framework like React/Vue)
            loadCustomers(); // Refresh list to show active state correctly
        }

        async function syncCustomers() {
            try {
                const response = await fetch(`${API_URL}/customers/sync-lexware`, { method: "POST" });
                const result = await response.json();
                showToast(result.message, "success");
                loadCustomers();
            } catch (error) {
                showToast("Sync fehlgeschlagen: " + error.message, "error");
            }
        }

        async function createCustomer() {
            const name = document.getElementById("newCustomerName").value;
            const email = document.getElementById("newCustomerEmail").value;
            const phone = document.getElementById("newCustomerPhone").value;
            const city = document.getElementById("newCustomerCity").value;

            if (!name || !email) {
                showToast("Name und E-Mail sind Pflichtfelder", "error");
                return;
            }

            try {
                const response = await fetch(`${API_URL}/customers`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, email, phone, city })
                });

                if (!response.ok) throw new Error("Fehler beim Anlegen");

                showToast("Kunde erfolgreich angelegt", "success");
                closeModal();
                
                // Clear form
                document.getElementById("newCustomerName").value = "";
                document.getElementById("newCustomerEmail").value = "";
                document.getElementById("newCustomerPhone").value = "";
                document.getElementById("newCustomerCity").value = "";

                loadCustomers();
            } catch (error) {
                showToast(error.message, "error");
            }
        }

        // --- Document Generation ---

        async function generateDocument() {
            if (!selectedCustomerId) {
                showToast("Bitte wähle zuerst einen Kunden aus der Liste", "error");
                return;
            }

            const prompt = document.getElementById("documentPrompt").value;
            if (!prompt) {
                showToast("Bitte gib Anweisungen für das Dokument ein", "error");
                return;
            }

            const docType = document.getElementById("docType").value;
            const btn = document.querySelector(".btn-generate");
            const originalText = btn.innerHTML;
            
            // Loading state
            btn.disabled = true;
            btn.innerHTML = "⏳ Generiere...";
            
            // Show loading in preview
            const preview = document.getElementById("previewContent");
            preview.innerHTML = `
                <div class="empty-state">
                    <div class="loading" style="width: 40px; height: 40px; border: 4px solid #e2e8f0; border-top-color: #3b82f6; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                    <h3 style="margin-top: 20px">KI arbeitet...</h3>
                    <p>Das Dokument wird erstellt.</p>
                </div>
                <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
            `;

            try {
                const response = await fetch(`${API_URL}/documents`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        customer_id: selectedCustomerId,
                        doc_type: docType,
                        prompt: prompt,
                        provider: "openai", // Hardcoded as requested
                        model: "gpt-4o-mini"
                    })
                });

                if (!response.ok) throw new Error("Generierung fehlgeschlagen");

                const document = await response.json();
                
                // Render Markdown (simple text replacement for now, ideally use a library)
                // For now, we just display it in a pre tag but styled nicely
                preview.innerHTML = `
                    <h2 style="margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px;">${document.title}</h2>
                    <div style="white-space: pre-wrap;">${document.content}</div>
                `;
                
                showToast("Dokument erstellt!", "success");

            } catch (error) {
                showToast(error.message, "error");
                preview.innerHTML = `
                    <div class="empty-state" style="color: #ef4444;">
                        <h3>Fehler</h3>
                        <p>${error.message}</p>
                    </div>
                `;
            } finally {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        }

        // --- UI Helpers ---

        function openModal() {
            document.getElementById("customerModal").style.display = "flex";
        }

        function closeModal() {
            document.getElementById("customerModal").style.display = "none";
        }

        function showToast(message, type) {
            const toast = document.getElementById("toast");
            toast.textContent = message;
            toast.className = `toast ${type}`;
            toast.style.display = "block";
            
            setTimeout(() => {
                toast.style.display = "none";
            }, 3000);
        }

        // Close modal on outside click
        document.getElementById("customerModal").addEventListener("click", (e) => {
            if (e.target === document.getElementById("customerModal")) {
                closeModal();
            }
        });
    </script>
</body>
</html>"""

with open("static/index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Successfully updated static/index.html")
