/**
 * E2E do fluxo critico: staff libera a mesa -> cliente e chamado.
 *
 * O cenario e criado via API (restaurante e mesa proprios) para nao depender do
 * seed nem de outros testes; as interacoes principais acontecem pela interface.
 */
import { expect, test, type APIRequestContext } from "@playwright/test";

const SENHA = "SenhaSegura12345";

function unico(prefixo: string): string {
  return `${prefixo}-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
}

async function csrf(request: APIRequestContext, baseURL: string): Promise<string> {
  const response = await request.get(`${baseURL}/api/auth/csrf`);
  const body = (await response.json()) as { csrf_token: string };
  return body.csrf_token;
}

async function postJson<T>(
  request: APIRequestContext,
  baseURL: string,
  path: string,
  data: unknown,
): Promise<T> {
  const token = await csrf(request, baseURL);
  const response = await request.post(`${baseURL}/api${path}`, {
    data: data ?? {},
    headers: { "X-CSRF-Token": token, "Content-Type": "application/json" },
  });
  expect(response.ok(), `${path} -> ${response.status()} ${await response.text()}`).toBeTruthy();
  return (await response.json()) as T;
}

test("staff libera mesa e o cliente na fila e chamado", async ({ browser, playwright }) => {
  const baseURL = test.info().project.use.baseURL as string;

  // ------------------------------------------------ cenario montado via API
  const setup = await playwright.request.newContext();
  const email = `${unico("admin")}@exemplo.com`;

  await postJson(setup, baseURL, "/auth/register", {
    email,
    password: SENHA,
    full_name: "Admin E2E",
  });
  await postJson(setup, baseURL, "/auth/login", { email, password: SENHA });

  const restaurante = await postJson<{ id: string; name: string }>(
    setup,
    baseURL,
    "/restaurants",
    {
      name: unico("Restaurante E2E"),
      address: "Rua dos Testes, 42",
      phone: "+551133330000",
      opening_hours: {},
    },
  );

  const mesa = await postJson<{ id: string; number: string }>(
    setup,
    baseURL,
    `/restaurants/${restaurante.id}/tables`,
    { number: "1", capacity: 4, pos_x: 0, pos_y: 0 },
  );

  // Mesa ocupada: assim o cliente entra na fila em vez de ser chamado na hora.
  await postJson(setup, baseURL, `/tables/${mesa.id}/occupy`, {});
  await setup.dispose();

  // ------------------------------------------------------- cliente entra na fila
  const clienteContexto = await browser.newContext();
  const cliente = await clienteContexto.newPage();
  await cliente.goto(`/restaurantes/${restaurante.id}`);

  await cliente.fill('input[name="customer_name"]', "Cliente E2E");
  await cliente.fill('input[name="customer_phone"]', `+5511${Date.now().toString().slice(-9)}`);
  await cliente.fill('input[name="party_size"]', "4");
  await cliente.getByTestId("entrar-fila").click();

  await expect(cliente).toHaveURL(/\/fila\//);
  await expect(cliente.getByTestId("ticket-position")).toContainText("#1");
  await expect(cliente.getByTestId("ticket-estimate")).toContainText("minutos");

  // ------------------------------------------------------- staff libera a mesa
  const staffContexto = await browser.newContext();
  const staff = await staffContexto.newPage();
  await staff.goto("/login?next=/staff");
  await staff.fill('input[name="email"]', email);
  await staff.fill('input[name="password"]', SENHA);
  await staff.getByRole("button", { name: "Entrar" }).click();

  await expect(staff).toHaveURL(/\/staff/);
  const cartaoMesa = staff.getByTestId("table-1");
  await expect(cartaoMesa).toHaveAttribute("data-status", "OCCUPIED");
  await cartaoMesa.click();

  await staff.getByTestId("liberar-mesa").click();

  // Toast confirma o grupo alocado automaticamente.
  await expect(staff.getByTestId("toast")).toContainText("Cliente E2E");
  await expect(cartaoMesa).toHaveAttribute("data-status", "RESERVED");

  // -------------------------------------------------- cliente ve que foi chamado
  await expect(cliente.getByTestId("called-title")).toContainText("Sua mesa esta pronta", {
    timeout: 20_000,
  });
  await expect(cliente.getByTestId("ticket-status")).toContainText("Chamado");

  // ------------------------------------------------ staff senta o cliente (SEATED)
  // A mesa continua selecionada apos a liberacao, entao a acao segue disponivel.
  await staff.getByTestId("ocupar-mesa").click();
  await expect(cartaoMesa).toHaveAttribute("data-status", "OCCUPIED");

  await clienteContexto.close();
  await staffContexto.close();
});
