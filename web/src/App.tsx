import { CardMetaProvider } from "./state/CardMetaContext";
import { GamePage } from "./pages/GamePage";

function App() {
  return (
    <CardMetaProvider>
      <header className="app-header">
        <h1>화투 Go-Stop</h1>
      </header>
      <GamePage />
    </CardMetaProvider>
  );
}

export default App;
