async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload ?? {}),
  });
  return response.json();
}

document.querySelectorAll("[data-job-endpoint]").forEach((button) => {
  button.addEventListener("click", async () => {
    const body = await postJson(button.dataset.jobEndpoint, {});
    const output = document.getElementById("debug-output");
    output.textContent = JSON.stringify(body, null, 2);
  });
});

const textSearchForm = document.getElementById("text-search-form");
if (textSearchForm) {
  textSearchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(textSearchForm);
    const payload = {
      query: String(formData.get("query") || ""),
      top_k: 5,
    };
    const body = await postJson("/api/debug/search/text", payload);
    document.getElementById("debug-output").textContent = JSON.stringify(body, null, 2);
  });
}
