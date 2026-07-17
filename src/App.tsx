import { BrowserRouter, Route, Routes } from "react-router";
import { ScrollToTop } from "./components/ScrollToTop";
import { FieldsHome } from "./pages/FieldsHome";
import { FieldPage } from "./pages/FieldPage";
import { SurveyPage } from "./pages/SurveyPage";
import { NotFound } from "./pages/NotFound";

// AppRoutes is the routing tree without the router, so tests can mount it under a
// MemoryRouter. App wires the real BrowserRouter. Three levels: fields, topics
// within a field, and the survey document itself.
export function AppRoutes() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<FieldsHome />} />
        <Route path="/:field" element={<FieldPage />} />
        <Route path="/:field/:topic" element={<SurveyPage />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
