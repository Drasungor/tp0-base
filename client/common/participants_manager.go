package common

import (
	// "bufio"
	"fmt"
	"net"
	// "time"
	// "os"
    // "os/signal"
    // "syscall"
	"encoding/binary"
	"io"
	"errors"

	// log "github.com/sirupsen/logrus"
)

const attributes_length_bytes_amount = 4
const message_type_code_bytes_amount = 1
const normal_message_code = 0
const error_message_code = 1
// const bool_bytes_amount = 1


type Participant struct {
	first_name string
	last_name string
	document string
	birthdate string
}

type ParticipantsManager struct {
	conn   net.Conn
	config ClientConfig
}

func NewParticipantsManager(config ClientConfig) (*ParticipantsManager, error) {
	conn, err := net.Dial("tcp", config.ServerAddress)
	if err != nil {
		return nil, err
	}
	manager := &ParticipantsManager {
		conn: conn,
		config: config,
	}
	return manager, nil
}

func (p *ParticipantsManager) senduint32(number uint32) error {
	message_lengh_buffer := make([]byte, attributes_length_bytes_amount)
	binary.BigEndian.PutUint32(message_lengh_buffer, number)
	_, err := p.conn.Write(message_lengh_buffer)
	return err
}

func (p *ParticipantsManager) sendString(message string) error {
	message_bytes := []byte(message)
	err := p.senduint32(uint32(len(message_bytes)))
	if err != nil {
		return err
	}
	_, err = p.conn.Write(message_bytes)
	return err
}

func (p *ParticipantsManager) readBytes(bytes_amount uint32) ([]byte, error) {
	bytes_buffer := make([]byte, bytes_amount)
	_, err := io.ReadFull(p.conn, bytes_buffer)
	return bytes_buffer, err
}

func (p *ParticipantsManager) readuint32() (uint32, error) {
	read_bytes, err := p.readBytes(4)
	if err != nil {
		return 0, err
	}
	return binary.BigEndian.Uint32(read_bytes), nil
}

func (p *ParticipantsManager) readString() (string, error) {
	bytes_amount, err := p.readuint32()
	if err != nil {
		return "", err
	}
	read_bytes, err := p.readBytes(bytes_amount)
	if err != nil {
		return "", err
	}
	return string(read_bytes), nil
}

func (p *ParticipantsManager) readByte() (byte, error) {
	byte_array, err := p.readBytes(1)
	if err != nil {
		return 0, err
	}
	return byte_array[0], nil
}

func (p *ParticipantsManager) SendParticipant() error {
	_, err := p.conn.Write([]byte{normal_message_code})
	if err != nil {
		return err
	}
	config := p.config
	participant_data := [4]string{config.FirstName, config.LastName, config.Document, config.Birthdate}
	for _, data := range participant_data {
		err = p.sendString(data)
		if err != nil {
			return err
		}
	}
	return nil
}

func (p *ParticipantsManager) ReceiveParticipantResult() (bool, bool, error) { // (Result, ApplicationError, error)
	code, err := p.readByte()
	if err != nil {
		return false, false, err
	}
	if code == error_message_code {
		message, err := p.readString()
		if err != nil {
			return false, false, err
		}
		return false, true, errors.New(message)
	} else if code == normal_message_code {
		received_result, err := p.readByte()
		if err != nil {
			return false, false, err
		}
		returned_result := received_result == 1
		if !returned_result && received_result != 0 {
			return false, false, fmt.Errorf("Received unexpected participation result %d", received_result)
		}
		return returned_result, false, nil
	} else {
		return false, false, fmt.Errorf("Received unexpected message type code %d", code)
	}
}

func (p *ParticipantsManager) CloseConnection() error {
	return p.conn.Close()
}