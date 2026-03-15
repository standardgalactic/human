export default function TabBar({ tabs, active, setActive }: { tabs: string[], active: string, setActive: (x:string)=>void }){
  return <div className="tabs">{tabs.map(t => <button key={t} className={t===active ? "tab active" : "tab"} onClick={()=>setActive(t)}>{t}</button>)}</div>
}
