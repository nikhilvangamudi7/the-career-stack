import { useState } from "react";

export default function Home(){
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [csvFile, setCsvFile] = useState(null);

  const backend = process.env.NEXT_PUBLIC_BACKEND_URL || "https://<RENDER_BACKEND_URL>";

  async function fetchLatest(){
    setLoading(true);
    try{
      const res = await fetch(`${backend}/api/fetch-latest?force=true`);
      const data = await res.json();
      setJobs(data.jobs || []);
    } catch(e){
      alert("Error: " + (e.message || e));
    } finally { setLoading(false); }
  }

  async function uploadCSV(e){
    e.preventDefault();
    if(!csvFile){ alert("Select CSV"); return; }
    const fd = new FormData(); fd.append("file", csvFile);
    setLoading(true);
    try{
      const res = await fetch(`${backend}/api/upload-csv`, { method: "POST", body: fd });
      const j = await res.json();
      alert("Uploaded: " + (j.message || JSON.stringify(j)));
    } catch(e){
      alert("Upload failed: " + (e.message || e));
    } finally { setLoading(false); }
  }

  return (
    <div style={{padding:20, fontFamily:"system-ui"}}>
      <h1>The Career Stack</h1>
      <p>Click <b>Fetch New Jobs (Today)</b> to generate fresh jobs from career pages.</p>

      <div style={{marginBottom:12}}>
        <button onClick={fetchLatest} disabled={loading}>🔁 Fetch New Jobs (Today)</button>
      </div>

      <form onSubmit={uploadCSV} style={{marginBottom:20}}>
        <input type="file" accept=".csv" onChange={(e)=>setCsvFile(e.target.files[0])} />
        <button type="submit" disabled={loading}>Upload CSV</button>
      </form>

      <hr/>
      <h2>Results ({jobs.length})</h2>
      <table border="1" cellPadding="6" style={{width:"100%", borderCollapse:"collapse"}}>
        <thead><tr><th>Company</th><th>Title</th><th>URL</th><th>When</th></tr></thead>
        <tbody>
          {jobs.map((j,i)=>(
            <tr key={i}>
              <td>{j.company}</td>
              <td>{j.title}</td>
              <td><a href={j.url} target="_blank" rel="noreferrer">Apply</a></td>
              <td>{j.scraped_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
