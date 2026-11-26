package labexp.semente.adapter.in.web;

import java.util.Map;
import labexp.semente.application.port.in.ConflitoIdempotenciaException;
import labexp.semente.application.port.in.TarefaNaoEncontradaException;
import labexp.semente.domain.TarefaInvalidaException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

@RestControllerAdvice
public class TratadorDeErros {

    @ExceptionHandler(TarefaInvalidaException.class)
    ResponseEntity<Map<String, String>> invalida(TarefaInvalidaException e) {
        return resposta(HttpStatus.BAD_REQUEST, "requisicao_invalida", e.getMessage());
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    ResponseEntity<Map<String, String>> ilegivel(HttpMessageNotReadableException e) {
        return resposta(HttpStatus.BAD_REQUEST, "requisicao_invalida", "corpo da requisicao invalido ou ausente");
    }

    @ExceptionHandler(TarefaNaoEncontradaException.class)
    ResponseEntity<Map<String, String>> naoEncontrada(TarefaNaoEncontradaException e) {
        return resposta(HttpStatus.NOT_FOUND, "nao_encontrada", e.getMessage());
    }

    @ExceptionHandler(ConflitoIdempotenciaException.class)
    ResponseEntity<Map<String, String>> conflito(ConflitoIdempotenciaException e) {
        return resposta(HttpStatus.UNPROCESSABLE_ENTITY, "conflito_de_chave", e.getMessage());
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    ResponseEntity<Map<String, String>> idMalformado(MethodArgumentTypeMismatchException e) {
        return resposta(HttpStatus.NOT_FOUND, "nao_encontrada", "tarefa nao encontrada");
    }

    private static ResponseEntity<Map<String, String>> resposta(HttpStatus status, String erro, String mensagem) {
        return ResponseEntity.status(status).body(Map.of("erro", erro, "mensagem", mensagem));
    }
}
