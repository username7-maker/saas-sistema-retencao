import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { NewAssessmentPage } from "../pages/assessments/NewAssessmentPage";

function LocationEcho() {
  const location = useLocation();
  return <div>{`${location.pathname}${location.search}`}</div>;
}

describe("NewAssessmentPage", () => {
  it("shows the two assessment modes instead of auto-redirecting", async () => {
    render(
      <MemoryRouter initialEntries={["/assessments/new/member-1"]}>
        <Routes>
          <Route path="/assessments/new/:memberId" element={<NewAssessmentPage />} />
          <Route path="/assessments/members/:memberId" element={<LocationEcho />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("button", { name: /com bioimpedancia/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sem bioimpedancia/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /com bioimpedancia/i }));

    expect(await screen.findByText("/assessments/members/member-1?tab=bioimpedancia")).toBeInTheDocument();
  });
});
