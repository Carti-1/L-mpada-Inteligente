# Firmware ESP32

O sketch `esp32_template.ino` contém o fluxo de publicação, mas a leitura física depende do modelo dos sensores e da pinagem. Complete `readSensors()` depois de confirmar o circuito.

Crie no Arduino IoT Cloud as variáveis `temperature`, `humidity`, `luminosity`, `tankLevel`, `color` e `buttonState`. Configure os tipos e a permissão de cada variável de acordo com o sketch. O arquivo gerado `thingProperties.h` contém identificadores da conta e fica ignorado pelo Git; não publique credenciais.

Instale também a biblioteca ArduinoJson. Copie `secrets.example.h` para `secrets.h` e configure o endereço do backend (acessível pela rede do ESP32) e a mesma chave `API_KEY` definida no `.env` do backend. O `.gitignore` exclui `secrets.h` e `thingProperties.h`.

O template sincroniza as variáveis com `ArduinoCloud.update()` e envia o pacote JSON para `POST /api/v1/readings` a cada cinco segundos. Ele considera HTTP `201` como confirmação; quando falha, tenta novamente no próximo ciclo. Configure a API atrás de HTTPS quando a conexão passar da rede local. Confira a disponibilidade de `tankLevel` e dos nomes/tipos das variáveis geradas pela sua Thing antes de compilar.
