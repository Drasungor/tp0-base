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
	// "golang.org/x/text/encoding/charmap"
	// log "github.com/sirupsen/logrus"
)

const uint32_length = 4
const bool_length = 1
const attributes_length_bytes_amount = uint32_length
const message_type_code_bytes_amount = 1
const normal_message_code = 0
const error_message_code = 1
const last_participant_delimiter = 0xFFFFFFFF

const connection_type_bytes_amount = 1
const contestants_evaluation_connection = 0
const winners_amount_connection = 1

const is_final_answer = 1
const connections_still_exist = 0


type Participant struct {
	first_name string
	last_name string
	document string
	birthdate string
}

type ParticipantsManager struct {
	conn        net.Conn
	config      ClientConfig
	fileReader  *csv.Reader
	file_ptr    *os.File
	closed      bool
}

func NewParticipantsManager(config ClientConfig) (*ParticipantsManager, error) {
	conn, err := net.Dial("tcp", config.ServerAddress)
	if err != nil {
		return nil, err
	}
	_, err = conn.Write([]byte{contestants_evaluation_connection})
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
		file_ptr: file,
		closed: false,
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

func (p *ParticipantsManager) SendParticipants() (int, bool, error) { // (ParticipantsSentAmount, HasFileFinished, error)
	_, err := p.conn.Write([]byte{normal_message_code})
	if err != nil {
		return 0, false, err
	}
	read_lines_amount := 1
	line_data, err := p.fileReader.Read()
	file_has_finished := false
	for (read_lines_amount <= int(p.config.BatchSize)) && err == nil {
		for _, data := range line_data {
			err = p.sendString(data)
			// log.Infof("csv line : %v", data)
			if err != nil {
				return read_lines_amount, false, err
			}
		}
		if (read_lines_amount < int(p.config.BatchSize)) {
			line_data, err = p.fileReader.Read()
		}
		read_lines_amount++
	}
	file_has_finished = (err == io.EOF)
	if err == nil || file_has_finished {
		err = p.senduint32(last_participant_delimiter)
	}
	if file_has_finished {
		return read_lines_amount - 1, true, nil
	} else  {
		return read_lines_amount - 1, false, err
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
	if !p.closed {
		err := p.file_ptr.Close()
		if err != nil {
			p.conn.Close()
			return err
		}
		err = p.conn.Close()
		if err != nil {
			return err
		}
		p.closed = true
	}
	return nil
}
