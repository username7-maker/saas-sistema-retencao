import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { NewAssessmentPage } from "../pages/assessments/NewAssessmentPage";

function LocationEcho() {
  const location = useLocation();
  return <div>{`${location.pathname}${location.search}`}</div>;
}

describe("NewAssessmentPage", () => {
  it("redirects to the member workspace register tab", async () => {
    render(
      <MemoryRouter initialEntries={["/assessments/new/member-1"]}>
        <Routes>
          <Route path="/assessments/new/:memberId" element={<NewAssessmentPage />} />
          <Route path="/assessments/members/:memberId" element={<LocationEcho />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("/assessments/members/member-1?tab=registro")).toBeInTheDocument();
  });
});
