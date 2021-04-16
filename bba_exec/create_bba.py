import sys

def main():
	with open(sys.argv[1], "rb") as f:
		data = f.read()
	with open(sys.argv[2], "w") as bbaf:
		print("push blob", file=bbaf)
		print("ref blob_data", file=bbaf)
		print("label func", file=bbaf)
		for b in data:
			print("u8 {}".format(b), file=bbaf)
		if (len(data) % 4) != 0:
			for i in range((len(data) % 4), 4):
				print("u8 0", file=bbaf) # 4-byte align
		print("label blob_data", file=bbaf)
		print("u32 1", file=bbaf) # version
		print("ref func", file=bbaf) # function pointer
		print("u32 {}".format(len(data)), file=bbaf) # function length
		print("pop", file=bbaf)

if __name__ == '__main__':
	main()
