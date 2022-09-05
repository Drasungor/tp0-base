package common

import (
	// "bufio"
	"fmt"
	"net"
	// "time"
	"os"
    // "os/signal"
    // "syscall"
	"encoding/binary"
	"io"
	"errors"
	"encoding/csv"

	// log "github.com/sirupsen/logrus"
)

const attributes_length_bytes_amount = 4
const message_type_code_bytes_amount = 1
const normal_message_code = 0
const error_message_code = 1
const last_participant_delimiter = 0xFFFFFFFF
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
	fileReader *csv.Reader
}

func NewParticipantsManager(config ClientConfig) (*ParticipantsManager, error) {
	conn, err := net.Dial("tcp", config.ServerAddress)
	if err != nil {
		return nil, err
	}
	file, error_message := os.Open(config.DatasetPath)
	if error_message != nil {
		conn.Close()
		return nil, err
	}
	manager := &ParticipantsManager {
		conn: conn,
		config: config,
		fileReader: csv.NewReader(file),
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

func (p *ParticipantsManager) SendParticipants() (bool, error) { // (HasFileFinished, error)
	_, err := p.conn.Write([]byte{normal_message_code})
	if err != nil {
		return false, err
	}
	read_lines_amount := 1
	line_data, current_error := p.fileReader.Read()
	for (read_lines_amount <= int(p.config.BatchSize)) && current_error != nil {
		for _, data := range line_data {
			err = p.sendString(data)
			if err != nil {
				return false, err
			}
		}
		line_data, current_error = p.fileReader.Read()
		read_lines_amount++
	}
	if err != nil || err == io.EOF {
		err = p.senduint32(last_participant_delimiter)
	}
	if err == nil {
		return false, nil
	} else if err == io.EOF {
		return true, nil
	} else {
		return false, err
	}
}

func (p *ParticipantsManager) readAllResults() ([]Participant, error) {
	winners := []Participant{}
	read_number, err := p.readuint32()
	if err != nil {
		return nil, err
	}
	for read_number != last_participant_delimiter {
		participant_first_name_bytes, err := p.readBytes(read_number)
		if err != nil {
			return nil, err
		}
		participant_last_name, err := p.readString()
		if err != nil {
			return nil, err
		}
		participant_document, err := p.readString()
		if err != nil {
			return nil, err
		}
		participant_birthdate, err := p.readString()
		if err != nil {
			return nil, err
		}
		participant := Participant {
			first_name: string(participant_first_name_bytes),
			last_name: participant_last_name,
			document: participant_document,
			birthdate: participant_birthdate,
		}
		winners = append(winners, participant)
		read_number, err = p.readuint32()
		if err != nil {
			return nil, err
		}
	}
	return winners, nil
}

func (p *ParticipantsManager) ReceiveWinningParticipants() ([]Participant, bool, error) { // (Result, ApplicationError, error)
	code, err := p.readByte()
	if err != nil {
		return nil, false, err
	}
	if code == error_message_code {
		message, err := p.readString()
		if err != nil {
			return nil, false, err
		}
		return nil, true, errors.New(message)
	} else if code == normal_message_code {
		results, err := p.readAllResults()
		if err != nil {
			return nil, false, err
		}
		return results, false, nil
	} else {
		return nil, false, fmt.Errorf("Received unexpected message type code %d", code)
	}
}

func (p *ParticipantsManager) CloseConnection() error {
	return p.conn.Close()
}