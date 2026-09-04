import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Sidebar from "@/components/Sidebar";
import Dashboard from "@/pages/Dashboard";
import KnowledgeBase from "@/pages/KnowledgeBase";
import Query from "@/pages/Query";
import Traces from "@/pages/Traces";
import PrivacyAudit from "@/pages/PrivacyAudit";
import Benchmarks from "@/pages/Benchmarks";

function Layout() {
  return (
    <div className="flex h-screen bg-[#0F0F0F] text-[#F2F2F2]" data-testid="app-shell">
      <Sidebar />
      <main className="flex-1 flex overflow-hidden">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/knowledge" element={<KnowledgeBase />} />
          <Route path="/query" element={<Query />} />
          <Route path="/traces" element={<Traces />} />
          <Route path="/privacy" element={<PrivacyAudit />} />
          <Route path="/benchmarks" element={<Benchmarks />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Layout />
        <Toaster theme="dark" position="top-right" />
      </BrowserRouter>
    </div>
  );
}
