package labexp.aceitacao.p9;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Servico externo simulado de P9. A aplicacao sob teste o alcanca por NOTIFICACAO_URL.
 *
 * <p>O contrato do pedido (par/impar) tem a tabela e a frase em desacordo sobre qual posicao responde 200.
 * Para os testes serem deterministas sem depender dessa leitura, o resultado e escolhido pelo proprio
 * teste ({@link Modo}), nao por contagem. Aceita POST em qualquer caminho (a URL configurada pode ou nao
 * terminar em /notificacoes).
 */
final class ServicoExternoStub implements AutoCloseable {

    enum Modo { OK_200, ERRO_503, LENTO }

    static final int PORTA = Integer.parseInt(System.getenv().getOrDefault("STUB_PORTA", "9099"));
    static final long ATRASO_LENTO_MS = 4000;

    private final HttpServer servidor;
    private final AtomicReference<Modo> modo = new AtomicReference<>(Modo.OK_200);
    private final AtomicInteger requisicoes = new AtomicInteger();

    ServicoExternoStub() {
        try {
            servidor = HttpServer.create(new InetSocketAddress(PORTA), 0);
        } catch (IOException e) {
            throw new IllegalStateException("nao foi possivel abrir o stub na porta " + PORTA, e);
        }
        servidor.setExecutor(Executors.newCachedThreadPool());
        servidor.createContext("/", troca -> {
            try (troca) {
                troca.getRequestBody().readAllBytes();
                requisicoes.incrementAndGet();
                Modo atual = modo.get();
                if (atual == Modo.LENTO) {
                    Thread.sleep(ATRASO_LENTO_MS);
                }
                int status = atual == Modo.ERRO_503 ? 503 : 200;
                byte[] corpo = (status == 200 ? "{\"ok\":true}" : "{\"ok\":false}").getBytes();
                troca.getResponseHeaders().add("Content-Type", "application/json");
                troca.sendResponseHeaders(status, corpo.length);
                troca.getResponseBody().write(corpo);
            } catch (IOException | InterruptedException ignorado) {
                // o cliente pode desistir antes (timeout de 500 ms): isso faz parte do cenario
            }
        });
        servidor.start();
    }

    void modo(Modo novo) {
        modo.set(novo);
        requisicoes.set(0);
    }

    int requisicoes() {
        return requisicoes.get();
    }

    @Override
    public void close() {
        servidor.stop(0);
    }
}
