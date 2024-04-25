# Wireguard Peer Monitoring

This project uses [Linux kernel dynamic debug](https://www.kernel.org/doc/html/latest/admin-guide/dynamic-debug-howto.html) features to capture and process Wireguard events and monitor peer activity.

This assumes that `debugfs` is mounted under `/sys/kernel/debug`.

## How to

1. First, you need to enable Wireguard debug logs. You can do this by running the following command:

    ```bash
    echo 'module wireguard +p' | sudo tee /sys/kernel/debug/dynamic_debug/control
    ```

2. Configure rsyslog to capture the logs. You can do this by adding the following line to `/etc/rsyslog.d/99-wireguard.conf`:

    ```bash
    kern.*  @127.0.0.1:9999
    ```

## Events

- wg_cookie_message_consume: `Could not decrypt invalid cookie response`
- send4: `No route to <IP:PORT>, error <ERROR CODE>`
- send6: `No route to <IP:PORT>, error <ERROR CODE>`
- wg_receive_handshake_packet: `Receiving cookie response from <IP:PORT>`
- wg_receive_handshake_packet: `Invalid MAC of handshake, dropping packet from <IP:PORT>`
- wg_receive_handshake_packet: `Invalid handshake initiation from <IP:PORT>`
- wg_receive_handshake_packet: `Receiving handshake initiation from peer <PEER ID> (<IP:PORT>)`
- wg_receive_handshake_packet: `Invalid handshake response from <IP:PORT>`
- wg_receive_handshake_packet: `Receiving handshake response from peer <PEER ID> (<IP:PORT>)`
- wg_packet_consume_data_done: `Receiving keepalive packet from peer <PEER ID> (<IP:PORT>)`
- wg_packet_consume_data_done: `Packet has unallowed src IP <IP> from peer <PEER ID> (<IP:PORT>)`
- wg_packet_consume_data_done: `Packet is neither ipv4 nor ipv6 from peer <PEER ID> (<IP:PORT>)`
- wg_packet_consume_data_done: `Packet has incorrect size from peer <PEER ID> (<IP:PORT>)`
- wg_packet_rx_poll: `Packet has invalid nonce <PEER ID> (max <PEER ID>)`
- wg_packet_receive: `Dropping handshake packet from <IP:PORT>`
- wg_packet_send_handshake_initiation: `Sending handshake initiation to peer <PEER ID> (<IP:PORT>)`
- wg_packet_send_handshake_response: `Sending handshake response to peer <PEER ID> (<IP:PORT>)`
- wg_packet_send_handshake_cookie: `Sending cookie response for denied handshake message for <IP:PORT>`
- wg_packet_send_keepalive: `Sending keepalive packet to peer <PEER ID> (<IP:PORT>)`
- wg_expired_retransmit_handshake: `Handshake for peer <PEER ID> (<IP:PORT>) did not complete after <TRY NUMBER> attempts, giving up`
- wg_expired_retransmit_handshake: `Handshake for peer <PEER ID> (<IP:PORT>) did not complete after <SEC> seconds, retrying (try <TRY NUMBER>)`
- wg_expired_new_handshake: `Retrying handshake with peer <PEER ID> (<IP:PORT>) because we stopped hearing back after <SEC> seconds`
- wg_queued_expired_zero_key_material: `Zeroing out all keys for peer <PEER ID> (<IP:PORT>), since we haven't received a new one in <SEC> seconds`
- wg_peer_create: `Peer <PEER ID> created`
- kref_release: `Peer <PEER ID> (<IP:PORT>) destroyed`
- wg_xmit: `Invalid IP packet`
- wg_xmit: `No peer has allowed IPs matching <IPv4>`
- wg_xmit: `No peer has allowed IPs matching <IPv6>`
- wg_xmit: `No valid endpoint has been configured or discovered for peer <PEER ID>`
- wg_destruct: `Interface destroyed`
- wg_newlink: `Interface created`
- wg_netns_pre_exit: `Creating namespace exiting`
- keypair_free_kref: `Keypair <PEER ID> destroyed for peer <PEER ID>`
- wg_noise_handshake_begin_session: `Keypair <PEER ID> created for peer <PEER ID>`
