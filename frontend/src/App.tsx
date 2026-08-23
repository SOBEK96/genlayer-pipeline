import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Web3Provider } from "@/context/Web3Provider";
import { ToastProvider } from "@/context/ToastContext";
import { AmbientGlow } from "@/components/3d/AmbientGlow";
import { ToastViewport } from "@/components/ui/ToastViewport";
import { Layout } from "@/components/ui/Layout";
import { Dashboard } from "@/views/Dashboard";
import { ActionHub } from "@/views/ActionHub";
import { History } from "@/views/History";

export default function App() {
  return (
    <Web3Provider>
      <ToastProvider>
        <BrowserRouter>
          <AmbientGlow />
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/action" element={<ActionHub />} />
              <Route path="/history" element={<History />} />
              <Route path="*" element={<Dashboard />} />
            </Routes>
          </Layout>
          <ToastViewport />
        </BrowserRouter>
      </ToastProvider>
    </Web3Provider>
  );
}
