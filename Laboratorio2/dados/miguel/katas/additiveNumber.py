class Solution(object):
    def isAdditiveNumber(self, num: str) -> bool:
        def validaSequencia(primeiro_num: int, segundo_num: int, sobrando: str) -> bool:
            if not sobrando:
                return True
            
            soma_esperada = primeiro_num + segundo_num
            if soma_esperada > 0 and sobrando[0] == '0':
                return False

            for prox_num_length in range(1, len(sobrando) + 1):
                potencial_prox_num = int(sobrando[:prox_num_length])

                if potencial_prox_num == soma_esperada:
                    if validaSequencia(segundo_num, soma_esperada, sobrando[prox_num_length:]):
                        return True
            
            return False
        
        string_length = len(num)

        for primeiro_num_final in range(1, string_length - 1):
            if primeiro_num_final > 1 and num[0] == '0':
                break
            
            for segundo_num_final in range(primeiro_num_final + 1, string_length):
                if segundo_num_final - primeiro_num_final > 1 and num[primeiro_num_final] == '0':
                    continue

                primeiro_num = int(num[:primeiro_num_final])
                segundo_num = int(num[primeiro_num_final:segundo_num_final])

                if validaSequencia(primeiro_num, segundo_num, num[segundo_num_final:]):
                    return True
    
        return False
        