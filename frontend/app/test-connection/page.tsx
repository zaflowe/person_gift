"use client";
import { useState, useEffect } from 'react';

export default function TestPage() {
    const [status, setStatus] = useState("Checking...");
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        const checkConnection = async () => {
            try {
                setStatus("Fetching from 127.0.0.1:8000...");
                // Try to fetch OpenAPI spec which is always public
                const res = await fetch("http://127.0.0.1:8000/openapi.json");
                if (res.ok) {
                    const json = await res.json();
                    setStatus("SUCCESS");
                    setData(json.info);
                } else {
                    setStatus("FAILED: " + res.status);
                }
            } catch (err: any) {
                setStatus("NETWORK ERROR");
                setError(err.message);
            }
        };
        checkConnection();
    }, []);

    return (
        <div style={{ padding: 40, fontFamily: 'monospace' }}>
            <h1>Connectivity Diagnostic</h1>
            <div style={{ marginTop: 20, padding: 20, border: '1px solid #ccc' }}>
                <p><strong>Status:</strong> {status}</p>
                {error && <p style={{ color: 'red' }}><strong>Error:</strong> {error}</p>}
                {data && (
                    <pre style={{ background: '#eee', padding: 10 }}>
                        {JSON.stringify(data, null, 2)}
                    </pre>
                )}
            </div>
        </div>
    );
}
