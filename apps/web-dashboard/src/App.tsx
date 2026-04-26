import "./index.css";

export function App() {
  return (
    <main className="shell">
      <header>
        <h1>⚡ Spark Merchant Portal</h1>
        <div className="merchant-info">
          <span><strong>Cafe Glockenspiel</strong> (Munich)</span>
          <span className="status-online">● Live on Spark Cloud</span>
        </div>
      </header>

      <section className="dashboard-grid">
        {/* Mock Rule Interface */}
        <div className="card campaign-goals">
          <h2>AI Campaign Goals</h2>
          <p className="description">Set your business objectives. Our AI handles the creative execution.</p>
          
          <div className="goal-row">
            <label>Primary Goal</label>
            <select defaultValue="quiet_hours">
              <option value="quiet_hours">Fill Quiet Hours (Density Optimization)</option>
              <option value="loyalty">Reward Repeat Customers</option>
              <option value="inventory">Clear Specific Inventory (Perishables)</option>
            </select>
          </div>

          <div className="goal-row">
            <label>Max Discount Cap</label>
            <input type="range" min="5" max="50" defaultValue="25" />
            <span className="value">25%</span>
          </div>

          <div className="goal-row">
            <label>Auto-Trigger Threshold</label>
            <select defaultValue="unusually_quiet">
              <option value="quiet">Quiet (Density &lt; 0.4)</option>
              <option value="unusually_quiet">Unusually Quiet (Density &lt; 0.2)</option>
            </select>
          </div>

          <button className="btn-primary">Update AI Strategy</button>
        </div>

        {/* Real-time Analytics Mockup */}
        <div className="card analytics">
          <h2>Live Performance</h2>
          <div className="stats-row">
            <div className="stat">
              <span className="label">Generated</span>
              <span className="number">1,204</span>
            </div>
            <div className="stat">
              <span className="label">Redeemed</span>
              <span className="number">142</span>
            </div>
            <div className="stat highlight">
              <span className="label">Conv. Rate</span>
              <span className="number">11.8%</span>
            </div>
          </div>
          <div className="chart-placeholder">
            [ Real-time Density vs. Redemption Chart ]
          </div>
        </div>
      </section>

      <style>{`
        .shell { padding: 2rem; max-width: 1000px; margin: 0 auto; font-family: system-ui; }
        header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 1rem; margin-bottom: 2rem; }
        .status-online { color: #00c853; font-size: 0.8rem; margin-left: 1rem; }
        .dashboard-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
        .card { border: 1px solid #ddd; padding: 1.5rem; border-radius: 12px; background: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .description { color: #666; font-size: 0.9rem; margin-bottom: 1.5rem; }
        .goal-row { margin-bottom: 1.5rem; display: flex; flex-direction: column; gap: 0.5rem; }
        label { font-weight: 600; font-size: 0.85rem; text-transform: uppercase; color: #444; }
        select, input { padding: 0.8rem; border-radius: 6px; border: 1px solid #ccc; font-size: 1rem; }
        .btn-primary { background: #000; color: #fff; padding: 1rem; border: none; border-radius: 6px; cursor: pointer; width: 100%; font-weight: bold; }
        .stats-row { display: flex; justify-content: space-between; margin-bottom: 2rem; }
        .stat { text-align: center; }
        .stat .label { display: block; font-size: 0.7rem; text-transform: uppercase; color: #888; }
        .stat .number { font-size: 1.5rem; font-weight: bold; }
        .stat.highlight .number { color: #00c853; }
        .chart-placeholder { height: 150px; background: #f9f9f9; border: 1px dashed #ccc; display: flex; align-items: center; justify-content: center; color: #999; font-style: italic; }
      `}</style>
    </main>
  );
}
