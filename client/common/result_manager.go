package common


import (
	"net"
	"io"
	"encoding/binary"
	"fmt"
)


type ResultManager struct {
	connection_string string
}

func NewResultManager(connection_string string) *ResultManager {
	return &ResultManager{
		connection_string: connection_string,
	}
}

func (r *ResultManager) getWinnersAmount() (uint32, bool, error) { // (WinnersAmount, true, nil) || (PendingClients, false, nil) || (0, false, err)
	conn, err := net.Dial("tcp", r.connection_string)
	defer conn.Close()
	if err != nil {
		return 0, false, err
	}
	_, err = conn.Write([]byte{winners_amount_connection})
	if err != nil {
		return 0, false, err
	}
	bytes_buffer := make([]byte, uint32_length)
	_, err = io.ReadFull(conn, bytes_buffer)
	if err != nil {
		return 0, false, err
	}
	received_number := binary.BigEndian.Uint32(bytes_buffer)
	bytes_buffer = make([]byte, bool_length)
	_, err = io.ReadFull(conn, bytes_buffer)
	if err != nil {
		return 0, false, err
	}
	finisher := bytes_buffer[0]
	if finisher == is_final_answer {
		return received_number, true, nil
	} else if finisher == connections_still_exist {
		return received_number, false, nil
	} else {
		return 0, false, fmt.Errorf("Received unexpected winners amount finisher %d", finisher)
	}
}

