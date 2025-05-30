import { BrowserRouter, Routes, Route } from "react-router-dom"
import Home from "./pages/Home"
import NotFound from "./pages/NotFound"
import CreatePage from "./pages/CreatePage"
import StatusPage from "./pages/StatusPage"
import StatusDetailPage from "./pages/StatusDetailPage"
import HistoryPage from "./pages/HistoryPage"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
              <Home />
          }
        />
        <Route
          path="/create"
          element={
              <CreatePage />
          }
        />
        <Route
          path="/status"
          element={
              <StatusPage />
          }
        />
        <Route
          path="/status/:id"
          element={
              <StatusDetailPage />
          }
        />
        <Route
          path="/history"
          element={
              <HistoryPage />
          }
        />
        <Route path="*" element={<NotFound />}></Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App