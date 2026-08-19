import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { WorkspaceShell } from "./WorkspaceShell";

vi.mock("./MapCanvas", () => ({ MapCanvas: () => <div data-testid="map-canvas" /> }));

describe("WorkspaceShell", () => {
  it("présente le parcours décisionnel et l'état du moteur", () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { gcTime: Infinity } } });
    const view = render(
      <QueryClientProvider client={queryClient}>
        <WorkspaceShell
          apiState="online"
          territory={null}
          territoryLoading={false}
          territoryError={null}
          onTerritorySelect={() => undefined}
          layers={[]}
          visibleIds={new Set()}
          selectedLayerId={null}
          dataError={null}
          uploading={false}
          onUpload={() => undefined}
          onToggleLayer={() => undefined}
          onSelectLayer={() => undefined}
          onDeleteLayer={() => undefined}
          diagnosticLayerId=""
          diagnosticDistance={500}
          scenarioLocations={[]}
          placingScenario={false}
          diagnosticRunning={false}
          diagnosticError={null}
          diagnosticResult={null}
          onDiagnosticLayerChange={() => undefined}
          onDiagnosticDistanceChange={() => undefined}
          onPlaceScenarioToggle={() => undefined}
          onScenarioMapClick={() => undefined}
          onClearScenario={() => undefined}
          onRunDiagnostic={() => undefined}
          expertOpen={false}
          onOpenExpert={() => undefined}
          onCloseExpert={() => undefined}
          onLayerUpdated={() => undefined}
          onLoadDemo={() => undefined}
          reportOpen={false}
          onOpenReport={() => undefined}
          onCloseReport={() => undefined}
        />
      </QueryClientProvider>,
    );

    expect(screen.getByText("Territorial Intelligence Studio")).toBeInTheDocument();
    expect(screen.getByText("Moteur disponible")).toBeInTheDocument();
    expect(screen.getByLabelText("Commune, code postal ou code INSEE")).toBeInTheDocument();
    expect(screen.getByRole("main", { name: "Espace cartographique" })).toBeInTheDocument();
    view.unmount();
    queryClient.clear();
  });
});
